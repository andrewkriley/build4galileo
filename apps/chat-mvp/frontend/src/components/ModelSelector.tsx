interface ModelSelectorProps {
  models: string[];
  selected: string;
  onChange: (model: string) => void;
}

export function ModelSelector({ models, selected, onChange }: ModelSelectorProps) {
  if (models.length === 0) {
    return <span className="provider-selector provider-selector--empty">no models available</span>;
  }

  return (
    <select
      className="provider-selector"
      value={selected}
      onChange={(event) => onChange(event.target.value)}
      aria-label="LLM model"
    >
      {models.map((model) => (
        <option key={model} value={model}>
          {model}
        </option>
      ))}
    </select>
  );
}
