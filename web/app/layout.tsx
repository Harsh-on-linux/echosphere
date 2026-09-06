import type { Metadata, Viewport } from "next";
import { Instrument_Sans } from "next/font/google";
import "@/index.css";

const instrumentSans = Instrument_Sans({
	subsets: ["latin"],
	display: "swap",
	variable: "--font-instrument-sans",
});

export const viewport: Viewport = {
	width: "device-width",
	initialScale: 1,
	maximumScale: 1,
};

export const metadata: Metadata = {
	title: "VaayuMitra — Bharat's Voice-Native मौसम Intelligence",
	description:
		"VaayuMitra is an IMD-grounded voice assistant for farmers, fishermen, and disaster teams — real-time district forecasts, cyclone and sea-state alerts in your language, powered by Agora's Conversational AI Engine.",
	icons: {
		icon: [
			{ url: "/favicon.ico" },
			{ url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
			{ url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
		],
		apple: [{ url: "/apple-touch-icon.png" }],
		other: [
			{
				url: "/android-chrome-192x192.png",
				sizes: "192x192",
				type: "image/png",
			},
			{
				url: "/android-chrome-512x512.png",
				sizes: "512x512",
				type: "image/png",
			},
		],
	},
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<html lang="en" className={`${instrumentSans.variable} h-full`}>
			<body className="h-full min-h-screen">{children}</body>
		</html>
	);
}
