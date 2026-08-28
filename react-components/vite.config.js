import react from "@vitejs/plugin-react";

export default {
  base: "./",
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: "./src/main.ts",
      name: "trame_rca_react",
      formats: ["umd"],
      fileName: "trame-rca-react",
    },
    // serve/ also holds the vue bundle
    emptyOutDir: false,
    rollupOptions: {
      external: ["react", "react-dom"],
      output: {
        globals: {
          react: "React",
          "react-dom": "ReactDOM",
        },
      },
    },
    outDir: "../src/trame_rca/module/serve",
    assetsDir: ".",
  },
};
