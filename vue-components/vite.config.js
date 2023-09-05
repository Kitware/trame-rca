export default {
  base: './',
  build: {
    lib: {
      entry: './src/use.js',
      name: 'trame_rca',
      formats: ['umd'],
      fileName: 'trame-rca',
    },
    rollupOptions: {
      external: ['vue'],
      output: {
        globals: {
          vue: 'Vue',
        },
      },
    },
    outDir: '../trame_rca/module/serve',
    assetsDir: '.',
    // sourcemap: true,
  },
};
