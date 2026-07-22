let text = 'waiting_to_start["Blocked\\n1"]';
let quotes = [];
let cleaned = text.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/g, (match) => {
  quotes.push(match.replace(/\r?\n/g, ' <br/> '));
  return `__QUOTE_${quotes.length - 1}__`;
});
console.log(cleaned);
console.log(quotes);
