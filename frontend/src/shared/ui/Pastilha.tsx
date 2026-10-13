/** Quadrado de cor que identifica uma configuração; o nome vem sempre ao lado (a cor nunca vai sozinha). */
export function Pastilha({ cor }: { cor: string }) {
  return <span className="pastilha" style={{ background: cor }} aria-hidden />;
}
