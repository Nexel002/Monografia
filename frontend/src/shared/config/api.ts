// Se a variável não estiver definida, assume-se a API local; o WebSocket deriva do mesmo endereço.
export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000";
export const WS_URL: string = API_URL.replace(/^http/, "ws");
