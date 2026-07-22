let code = `graph TB
    dharaneesh_r["Dharaneesh's Tasks (R: 2, A: 1, G: 1)"] -->|Blocked| blocked_task1["Task 1: Blocked"]
    blocked_task1 -->|Delayed| delayed_task1["Task 2: Delayed"]
    dharaneesh_r -->|In Progress| in_progress_task2["Task 3: In Progress"]
    dharaneesh_r -->|Complete| completed_task4["Task 4: Complete"]
Here, the RAG pipeline is visualized as a graph, where "dharaneesh_r" represents Dharaneesh's tasks, and the three nodes represent the Red (Blocked), Amber (In Progress), and Green (Complete) stages.
This is another sentence.
Alice -> Bob: Hello
participant Alice
subgraph A
A --> B`;

let cleaned = code.split('\n').filter(line => {
  const trimmed = line.trim();
  const match = /^([A-Za-z]+)(?:,|\s+)([A-Za-z]+)/.exec(trimmed);
  if (match) {
    const firstWord = match[1].toLowerCase();
    const validKeywords = [
      'subgraph', 'end', 'classdef', 'class', 'click', 'style', 'linkstyle', 'note', 'direction', 
      'graph', 'flowchart', 'pie', 'gantt', 'sequencediagram', 'classdiagram', 'statediagram', 
      'erdiagram', 'gitgraph', 'mindmap', 'timeline', 'c4diagram', 'participant', 'actor', 'state', 'title'
    ];
    if (!validKeywords.includes(firstWord)) {
      return false; // strip conversational text
    }
  }
  return true;
}).join('\n');

console.log(cleaned);
