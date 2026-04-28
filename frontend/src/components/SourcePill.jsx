import { FileText } from "lucide-react";

export default function SourcePill({ name }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full text-xs font-medium">
      <FileText className="w-3 h-3" aria-hidden />
      {name}
    </span>
  );
}
