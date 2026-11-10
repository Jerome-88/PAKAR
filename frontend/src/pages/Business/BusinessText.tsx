import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { readableText } from "./resultSummary";

export function BusinessText({ value, components }: { value: unknown; components?: Components }) {
  const text = readableText(value);
  return text ? <div className="business-readable-text"><ReactMarkdown skipHtml remarkPlugins={[remarkGfm]} components={{ ...components, img: ({ alt }) => <span>{alt || "Gambar dalam teks tidak dimuat."}</span> }}>{text}</ReactMarkdown></div> : <p>Penjelasan belum tersedia.</p>;
}
