let text = `waiting_to_start["Blocked
1
2]`;
text = text.replace(/\[\s*"([^"\]]*)]/g, '["$1"]');
console.log(text);
