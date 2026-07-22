const fs = require('fs');
let code = `graph LR
    tasks[New Task] -->|Move to Progress| >- red
    red["Red (Delayed/Ongoing Issues)"] -->|Move to Amber| >- amber
    amber["Amber (At Risk/ Needs Attention)"] -->|Move to Green| >- green
    green["Green (On Track/Completed)"]`;

function sanitizeMermaidCode(raw) {
  let cleaned = raw.trim();
  cleaned = cleaned.replace(/\|([^|]+)\|\s*(?:>-|->|-->|>)\s*/g, '|$1| ');
  cleaned = cleaned.replace(/>-/g, '-->');
  return cleaned;
}

console.log(sanitizeMermaidCode(code));
