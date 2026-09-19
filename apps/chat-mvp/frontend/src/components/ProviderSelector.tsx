interface ProviderSelectorProps {
  providers: string[];
  selected: string;
  onChange: (provider: string) => void;
}

export function ProviderSelector({ providers, selected, onChange }: ProviderSelectorProps) {
  if (providers.length === 0) {
    return <span className="provider-selector provider-selector--empty">no provider keys configured</span>;
  }

  return (
    <select
      className="provider-selector"
      value={selected}
      onChange={(event) => onChange(event.target.value)}
      aria-label="LLM provider"
    >
      {providers.map((provider) => (
        <option key={provider} value={provider}>
          {provider}
        </option>
      ))}
    </select>
  );
}
