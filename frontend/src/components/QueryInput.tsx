import { Badge } from "./ui/badge";
import { Textarea } from "./ui/textarea";

interface QueryInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

const examples = [
  "What are the latest trends in quantum computing?",
  "Analyze quarterly sales trends (upload CSV)",
  "Research AI safety developments and compare with industry data"
];

export function QueryInput({ value, onChange, onSubmit, disabled }: QueryInputProps) {
  return (
    <div className="space-y-4">
      <Textarea
        placeholder="What would you like to research?"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
        disabled={disabled}
        className="min-h-[120px] text-lg p-4"
      />
      
      {value.length > 100 && (
        <p className="text-sm text-muted-foreground">
          {value.length} characters
        </p>
      )}
      
      <div className="flex gap-2 flex-wrap">
        {examples.map((example) => (
          <Badge
            key={example}
            variant="outline"
            className="cursor-pointer hover:bg-accent py-1.5 px-3"
            onClick={() => onChange(example)}
          >
            {example.slice(0, 40)}...
          </Badge>
        ))}
      </div>
    </div>
  );
}
