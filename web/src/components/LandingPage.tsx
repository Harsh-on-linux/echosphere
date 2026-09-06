"use client";

import type { RTMClient } from "agora-rtm";
import dynamic from "next/dynamic";
import Image from "next/image";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { QuickstartPreCallCard } from "@/components/QuickstartPreCallCard";
import { SessionHistoryPanel } from "@/components/SessionHistoryPanel";
import { TelephonyPanel } from "@/components/TelephonyPanel";
import { VoiceSettingsPanel } from "@/components/VoiceSettingsPanel";
import type { VoiceSettings } from "@/components/VoiceSettingsPanel";
import { ShareButton } from "@/components/share-button";
import { saveSnapshot } from "@/lib/sessionHistory";
import { getAgentHistory, getAgentTurns, getConfig, startAgent, stopAgent } from "@/services/api";
import type { AgoraRenewalTokens, AgoraTokenData } from "@/types/conversation";

const ConversationComponent = dynamic(
	() => import("@/components/ConversationComponent"),
	{
		ssr: false,
	},
);

function waitForRtmConnected(rtmClient: RTMClient, timeoutMs = 600): Promise<void> {
	return new Promise((resolve) => {
		let settled = false;
		let timer: ReturnType<typeof setTimeout> | null = null;

		const finish = () => {
			if (settled) return;
			settled = true;
			if (timer) clearTimeout(timer);
			rtmClient.removeEventListener("status", onStatus);
			resolve();
		};

		const onStatus = (
			connectionStatus:
				| { newState?: string }
				| { state?: string }
				| Record<string, unknown>,
		) => {
			const nextState =
				typeof connectionStatus === "object" && connectionStatus !== null
					? "newState" in connectionStatus
						? connectionStatus.newState
						: "state" in connectionStatus
							? connectionStatus.state
							: undefined
					: undefined;
			if (nextState === "CONNECTED") {
				finish();
			}
		};

		rtmClient.addEventListener("status", onStatus);
		timer = setTimeout(finish, timeoutMs);
	});
}

const AgoraProvider = dynamic(
	async () => {
		const { AgoraRTCProvider, default: AgoraRTC } = await import(
			"agora-rtc-react"
		);

		return {
			default: function AgoraProviders({
				children,
			}: { children: React.ReactNode }) {
				const clientRef = useRef<ReturnType<
					typeof AgoraRTC.createClient
				> | null>(null);
				if (!clientRef.current) {
					clientRef.current = AgoraRTC.createClient({
						mode: "rtc",
						codec: "vp8",
					});
				}
				return (
					<AgoraRTCProvider client={clientRef.current}>
						{children}
					</AgoraRTCProvider>
				);
			},
		};
	},
	{ ssr: false },
);

export default function LandingPage() {
	const [showConversation, setShowConversation] = useState(false);
	const [agoraData, setAgoraData] = useState<AgoraTokenData | null>(null);
	const [rtmClient, setRtmClient] = useState<RTMClient | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [agentJoinError, setAgentJoinError] = useState(false);
	// Phase 4.2: pre-call voice preference -> startAgent language/persona.
	const [voiceSettings, setVoiceSettings] = useState<VoiceSettings | null>(null);
	// Phase 1.3: GPS Geolocation state
	const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
	const [isLocating, setIsLocating] = useState(false);
	// Phase 6.2: session start for the persisted history snapshot.
	const startedAtRef = useRef<number>(0);
	const isEndingRef = useRef<boolean>(false);

	const handleToggleLocation = () => {
		if (coords) {
			setCoords(null);
			return;
		}
		if (typeof window === "undefined" || !navigator.geolocation) {
			setError("Geolocation is not supported by your browser");
			return;
		}
		setIsLocating(true);
		navigator.geolocation.getCurrentPosition(
			(pos) => {
				setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
				setIsLocating(false);
			},
			(err) => {
				console.warn("GPS lookup failed:", err.message);
				setIsLocating(false);
			},
			{ timeout: 10000, enableHighAccuracy: true },
		);
	};

	useEffect(() => {
		import("agora-rtc-react").catch(() => {});
		import("agora-rtm").catch(() => {});
	}, []);

	// Phase 2.3 leave guard: if the tab closes mid-conversation, best-effort
	// stop the agent so minutes do not burn until idle_timeout (120s) fires.
	useEffect(() => {
		if (!showConversation || !agoraData?.agentId) return;
		const agentId = agoraData.agentId;
		const handlePageHide = () => {
			try {
				const blob = new Blob([JSON.stringify({ agentId })], {
					type: "application/json",
				});
				navigator.sendBeacon("/api/stopAgent", blob);
			} catch {
				// Best-effort only; idle_timeout is the backstop.
			}
		};
		window.addEventListener("pagehide", handlePageHide);
		return () => window.removeEventListener("pagehide", handlePageHide);
	}, [showConversation, agoraData?.agentId]);

	const handleStartConversation = async () => {
		setIsLoading(true);
		setError(null);
		setAgentJoinError(false);

		try {
			const config = await getConfig();
			const appId = config.app_id;

			const [agentIdResult, rtm] = await Promise.all([
				startAgent(
					config.channel_name,
					Number(config.agent_uid),
					Number(config.uid),
					{
						language: voiceSettings?.asrLanguage,
						persona: voiceSettings?.persona,
						lat: coords?.lat,
						lon: coords?.lon,
						voice: voiceSettings?.ttsVoice,
					},
				).catch((err) => {
					console.error("Failed to start conversation with agent:", err);
					setAgentJoinError(true);
					return undefined;
				}),
				(async () => {
					const { default: AgoraRTM } = await import("agora-rtm");
					const nextRtm: RTMClient = new AgoraRTM.RTM(appId, config.uid);
					await nextRtm.login({ token: config.token });
					await waitForRtmConnected(nextRtm);
					await nextRtm.subscribe(config.channel_name);
					return nextRtm;
				})(),
			]);

		setRtmClient(rtm);
		startedAtRef.current = Date.now();
		const isSarvam =
			voiceSettings?.ttsVoice === "anushka" ||
			(Boolean(voiceSettings?.asrLanguage) && voiceSettings?.asrLanguage !== "en-IN");

		setAgoraData({
				token: config.token,
				uid: config.uid,
				channel: config.channel_name,
				appId: config.app_id,
				agentUid: config.agent_uid,
				agentId: agentIdResult,
				sttVendor: isSarvam ? "sarvam" : "deepgram",
				ttsVendor: isSarvam ? "sarvam" : "minimax",
			});
			setShowConversation(true);
		} catch (nextError) {
			setError("Failed to start conversation. Please try again.");
			console.error("Error starting conversation:", nextError);
		} finally {
			setIsLoading(false);
		}
	};

	const handleTokenWillExpire = useCallback(
		async (uid: string): Promise<AgoraRenewalTokens> => {
			try {
				const channel = agoraData?.channel;
				if (!channel) {
					throw new Error("Missing channel for token renewal");
				}

				// Python get_config issues RTM-capable tokens for the configured account,
				// so renew RTM with the same UID used by the RTM client login.
				const [rtcConfig, rtmConfig] = await Promise.all([
					getConfig({ channel, uid }),
					getConfig({ channel, uid: agoraData.uid }),
				]);

				return {
					rtcToken: rtcConfig.token,
					rtmToken: rtmConfig.token,
				};
			} catch (error) {
				console.error("Error renewing token:", error);
				throw error;
			}
		},
		[agoraData],
	);

	const handleEndConversation = async () => {
		if (isEndingRef.current) return;
		isEndingRef.current = true;
		try {
			// Phase 6.2: persist history + turns for post-demo analytics (best-effort,
			// never blocks leave). Snapshot first so a failing stopAgent can't lose it.
			const snapshotAgentId = agoraData?.agentId;
			const snapshotChannel = agoraData?.channel ?? "";
			if (snapshotAgentId) {
				try {
					const [history, turns] = await Promise.all([
						getAgentHistory(snapshotAgentId).catch(() => null),
						getAgentTurns(snapshotAgentId, { pageSize: 50 }).catch(() => null),
					]);
					saveSnapshot({
						agentId: snapshotAgentId,
						channel: snapshotChannel,
						startedAt: startedAtRef.current || Date.now(),
						endedAt: Date.now(),
						language: voiceSettings?.asrLanguage,
						persona: voiceSettings?.persona,
						history,
						turns,
					});
				} catch {
					// Persistence must never break conversation teardown.
				}
			}

			if (agoraData?.agentId) {
				try {
					await stopAgent(agoraData.agentId);
				} catch (nextError) {
					console.error("Failed to stop agent:", nextError);
				}
			}

			rtmClient?.logout().catch((err) => console.error("RTM logout error:", err));
			setRtmClient(null);
			setAgoraData(null);
			setShowConversation(false);
		} finally {
			isEndingRef.current = false;
		}
	};

	return (
		<div className="vm-monsoon-bg relative flex h-dvh min-h-screen flex-col overflow-hidden text-foreground">
			<div className="vm-grid-overlay pointer-events-none absolute inset-0" aria-hidden />
			<div className="vm-drift pointer-events-none absolute -top-24 left-[8%] h-72 w-72 rounded-full bg-primary/15 blur-3xl" aria-hidden />
			<div className="pointer-events-none absolute right-[4%] top-[30%] h-80 w-80 rounded-full bg-accent/10 blur-3xl" aria-hidden />
			<div
				className={`flex min-h-0 flex-1 flex-col ${
					showConversation
						? "items-stretch justify-start"
						: "items-center justify-center"
				}`}
			>
				<div
					className={`z-10 flex min-h-0 flex-1 flex-col ${
						showConversation
							? "h-full w-full max-w-none items-stretch gap-0 px-0 text-left"
							: "w-full max-w-none items-center justify-center px-4 text-center"
					}`}
				>
					{!showConversation ? (
						<div className="z-10 min-h-0 w-full flex-1 overflow-y-auto">
							<div className="mx-auto grid w-[min(94vw,62rem)] gap-4 px-1 pb-32 pt-6 sm:pt-10 lg:grid-cols-2 lg:items-start">
								<div className="flex min-w-0 flex-col items-stretch gap-4">
									<QuickstartPreCallCard
										isLoading={isLoading}
										error={error}
										onStartConversation={handleStartConversation}
										coords={coords}
										onToggleLocation={handleToggleLocation}
										isLocating={isLocating}
									/>
									<VoiceSettingsPanel onChange={setVoiceSettings} />
								</div>
								<div className="flex min-w-0 flex-col items-stretch gap-4">
									<SessionHistoryPanel />
									<TelephonyPanel />
								</div>
							</div>
						</div>
					) : agoraData && rtmClient ? (
						<>
							{agentJoinError ? (
								<div className="max-w-sm rounded-md bg-destructive/10 p-3 text-sm text-destructive">
									Failed to connect with AI agent. The conversation may not work
									as expected.
								</div>
							) : null}
							<Suspense fallback={<LoadingSkeleton />}>
								<ErrorBoundary>
									<AgoraProvider>
										<ConversationComponent
											agoraData={agoraData}
											rtmClient={rtmClient}
											onTokenWillExpire={handleTokenWillExpire}
											onEndConversation={handleEndConversation}
										/>
									</AgoraProvider>
								</ErrorBoundary>
							</Suspense>
						</>
					) : (
						<p className="text-sm text-muted-foreground">
							Failed to load conversation data.
						</p>
					)}
				</div>
			</div>

			<footer
				className={`fixed inset-x-0 bottom-0 z-40 flex items-center gap-4 px-4 py-4 md:px-6 md:py-6 ${
					showConversation ? "justify-end" : "justify-between"
				}`}
			>
				{!showConversation ? <ShareButton menuPlacement="top" /> : null}
				<div className="flex items-center justify-end gap-2 text-muted-foreground">
					<span className="text-xs font-medium uppercase tracking-wide">
						Powered by
					</span>
					<a
						href="https://agora.io/en/"
						target="_blank"
						rel="noopener noreferrer"
						className="transition-colors hover:text-primary"
						aria-label="Visit Agora's website"
					>
						<Image
							src="/agora-logo-rgb-blue.svg"
							alt="Agora"
							width={86}
							height={24}
							priority
							className="h-6 w-auto translate-y-1 transition-opacity hover:opacity-80"
						/>
						<span className="sr-only">Agora</span>
					</a>
				</div>
			</footer>
		</div>
	);
}
