import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Porta fixa de propósito: a API só aceita (CORS) a origem http://localhost:5174. Com o Vite noutra
// porta a página carregava e todos os pedidos falhavam sem erro visível; `strictPort` troca isso por
// um erro claro no arranque.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, strictPort: true },
  test: { environment: "node" },
});
