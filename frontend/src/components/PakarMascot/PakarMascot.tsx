import "./PakarMascot.css";

export function PakarMascot({ name = "moki" }: { name?: "moki" | "lumi" | "noki" | "peb" | "kubo" }) {
  return <span className={`pakar-mascot pakar-mascot-${name}`} aria-hidden="true"><span><img src={`${import.meta.env.BASE_URL}figma/pakar/${name}.png`} alt="" /></span></span>;
}
