let code = `graph LR
    tasks[New Task] -->|Move to Progress| >- red
    red["Red (Delayed/Ongoing Issues)"] -->|Move to Amber| >- amber
    amber["Amber (At Risk/ Needs Attention)"] -->|Move to Green| >- green
    green["Green (On Track/Completed)"]`;

function sanitizeMermaidCode(raw) {
  let cleaned = raw.trim();

  cleaned = cleaned.replace(/\s+(\w+)\s*(-->|-.->|==>|->|->>)/g, '\n$1 $2');
  
  cleaned = cleaned.replace(/^```mermaid\s*/i, '');
  cleaned = cleaned.replace(/^```\s*/i, '');
  cleaned = cleaned.replace(/```$/, '');
  
  cleaned = cleaned.split('\n').map(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith('#') && !trimmed.startsWith('#rgba') && !trimmed.startsWith('#hex')) {
      return '%%' + line.slice(1);
    }
    return line;
  }).join('\n');

  const quotes = [];
  cleaned = cleaned.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/g, (match) => {
    quotes.push(match);
    return `__QUOTE_${quotes.length - 1}__`;
  });

  cleaned = cleaned.replace(/(\w+)\s*\[([^"\]\n]+)\]/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}["${text.trim().replace(/"/g, "'")}"]`;
  });
  cleaned = cleaned.replace(/(\w+)\s*\(([^")\n]+)\)/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}("${text.trim().replace(/"/g, "'")}")`;
  });
  cleaned = cleaned.replace(/(\w+)\s*\{([^"}\n]+)\}/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}{"${text.trim().replace(/"/g, "'")}"}`;
  });

  cleaned = cleaned.replace(/__QUOTE_(\d+)__/g, (match, id) => {
    return quotes[parseInt(id, 10)];
  });

  cleaned = cleaned.split('\n').map(line => {
    const trimmed = line.trim().toLowerCase();
    if (!trimmed.startsWith('sequencediagram')) {
      line = line.replace(/->>/g, '-->');
      line = line.replace(/(?<!-)->(?!>)/g, '-->');
      line = line.replace(/\|([^|]+)\|\s*(?:>-|->|-->|>)\s*/g, '|$1| ');
      line = line.replace(/>-/g, '-->');
    }
    return line;
  }).join('\n');

  const lower = cleaned.toLowerCase();
  const validStarts = [
    'graph', 'flowchart', 'sequencediagram', 'classdiagram', 
    'statediagram', 'erdiagram', 'gantt', 'pie', 'gitgraph', 
    'mindmap', 'timeline', 'c4diagram'
  ];
  const hasValidStart = validStarts.some(start => lower.startsWith(start));
  if (!hasValidStart) {
    cleaned = 'graph TD\n' + cleaned;
  }
  
  return cleaned.trim();
}

console.log(sanitizeMermaidCode(code));
