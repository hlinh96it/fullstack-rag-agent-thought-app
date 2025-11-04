import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
	plugins: [react(), tailwindcss()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
			"@repo": path.resolve(__dirname, "../../packages"),
			// Point @repo/shadcn-ui to local src to resolve e.g. @repo/shadcn-ui/components/ui/button
			"@repo/shadcn-ui": path.resolve(__dirname, "./src"),
		},
		resolve: {
			preserveSymlinks: true,
		},
	},
});
