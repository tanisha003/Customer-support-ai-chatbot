import { Package, Truck, CreditCard, MapPin } from "lucide-react";

/**
 * Topic chips shown inside the assistant's welcome message.
 * Hidden after the user sends their first message.
 *
 * Each suggestion has:
 *   - label: short text shown on the chip
 *   - question: the full question sent to the backend
 *   - icon: a Lucide React component
 */
const SUGGESTIONS = [
  {
    label: "Return policy",
    question: "What is your return window and how do I return an item?",
    Icon: Package,
  },
  {
    label: "Shipping times",
    question: "How long does shipping take?",
    Icon: Truck,
  },
  {
    label: "Payment methods",
    question: "What payment methods do you accept?",
    Icon: CreditCard,
  },
  {
    label: "Available cities",
    question: "In which cities is PrimeStay available?",
    Icon: MapPin,
  },
];

export default function SuggestedQuestions({ onSelect, disabled }) {
  return (
    <div className="grid grid-cols-2 gap-2 max-w-md mt-2">
      {SUGGESTIONS.map(({ label, question, Icon }) => (
        <button
          key={label}
          type="button"
          onClick={() => !disabled && onSelect(question)}
          disabled={disabled}
          className="flex items-center gap-2 px-3 py-2 bg-white border border-indigo-200 rounded-lg text-sm text-indigo-700 hover:bg-indigo-50 hover:border-indigo-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-left"
        >
          <Icon className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0" aria-hidden />
          <span className="truncate">{label}</span>
        </button>
      ))}
    </div>
  );
}

export { SUGGESTIONS };
