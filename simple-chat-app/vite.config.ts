import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server:{
    port: 3000,
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "aisecure.cmihandbook.com"
    ]
  },
  preview:{
    port: 3000,
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "aisecure.cmihandbook.com"
    ]
  }
})
