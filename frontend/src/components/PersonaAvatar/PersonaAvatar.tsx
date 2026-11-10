import { memo } from "react";
import type { AvatarIdentity } from "./avatar";
import { agentAvatarId, FALLBACK_AVATAR, getAvatarSource } from "./avatar";
import "./PersonaAvatar.css";

type Props = AvatarIdentity & { size?: number; className?: string };

// Decorative when paired with the visible persona name; never duplicate it for
// screen readers. Use this same source helper for SVG graph <image> elements.
export const PersonaAvatar = memo(function PersonaAvatar({ size = 36, className = "", ...identity }: Props) {
  return <img className={`persona-avatar ${className}`} src={getAvatarSource(identity)} alt="" aria-hidden="true" width={size} height={size} decoding="async" draggable={false} onError={event => { if (event.currentTarget.src !== FALLBACK_AVATAR) event.currentTarget.src = FALLBACK_AVATAR; }} />;
});

export function AgentIdentity({ name }: { name: string }) {
  return <span className="persona-identity"><PersonaAvatar id={agentAvatarId(name)} kind="agent" size={24} /><span>{name}</span></span>;
}

export function AvatarCredits() {
  return <details className="avatar-credits"><summary>Kredit ilustrasi avatar</summary><p>Ilustrasi identitas, bukan atribut demografis persona. <a href="https://personas.draftbit.com/" target="_blank" rel="noreferrer">Personas oleh Draftbit</a> dan <a href="https://www.figma.com/community/file/968125295144990435" target="_blank" rel="noreferrer">Fun Emoji oleh Davis Uche</a>, melalui <a href="https://www.dicebear.com/" target="_blank" rel="noreferrer">DiceBear</a>. Keduanya berlisensi <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>; warna, pilihan komponen, dan bingkai disesuaikan untuk PAKAR. <a href={`${import.meta.env.BASE_URL}avatar-licenses.txt`}>Lisensi dan pemberitahuan lengkap</a>.</p></details>;
}
