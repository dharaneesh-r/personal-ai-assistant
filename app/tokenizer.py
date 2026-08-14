import json
import re
from typing import List, Dict, Tuple

class BPETokenizer:
    """
    A GPT-4 style Byte Pair Encoding (BPE) algorithm from scratch.
    Includes Regex Pre-tokenization to prevent merging across spaces,
    punctuation, and distinct character types.
    """
    def __init__(self):
        # The merges dictionary maps pairs of tokens to a new token ID
        self.merges: Dict[Tuple[int, int], int] = {}
        
        # The vocabulary maps token IDs to their raw bytes
        self.vocab: Dict[int, bytes] = {idx: bytes([idx]) for idx in range(256)}
        
        # Basic GPT-2/4 style regex pattern for pre-tokenization
        # Splits by words, numbers, punctuation, and preserves leading spaces
        self.pat = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?[A-Za-z]+| ?[0-9]+| ?[^\sA-Za-z0-9]+|\s+(?!\S)|\s+""")
        
    def _get_stats(self, ids: List[int], counts: Dict[Tuple[int, int], int] = None) -> Dict[Tuple[int, int], int]:
        """
        Count the frequencies of all adjacent pairs of token IDs.
        """
        if counts is None:
            counts = {}
        for pair in zip(ids, ids[1:]):
            counts[pair] = counts.get(pair, 0) + 1
        return counts

    def _merge(self, ids: List[int], pair: Tuple[int, int], idx: int) -> List[int]:
        """
        Replaces all consecutive occurrences of `pair` in `ids` with `idx`.
        """
        newids = []
        i = 0
        while i < len(ids):
            if i < len(ids) - 1 and ids[i] == pair[0] and ids[i+1] == pair[1]:
                newids.append(idx)
                i += 2
            else:
                newids.append(ids[i])
                i += 1
        return newids

    def train(self, text: str, vocab_size: int, verbose: bool = False):
        """
        Train the tokenizer on a given text corpus using Regex Pre-tokenization.
        """
        assert vocab_size >= 256, "Vocabulary size must be at least 256."
        num_merges = vocab_size - 256
        
        if num_merges <= 0:
            return
            
        # 1. Pre-tokenize the text into independent chunks using Regex
        chunks = re.findall(self.pat, text)
        
        # 2. Convert each chunk to a list of integer IDs (0-255)
        chunk_ids = [list(chunk.encode("utf-8")) for chunk in chunks]
        
        # 3. Iteratively find the most frequent pair across all chunks and merge
        for i in range(num_merges):
            stats = {}
            for ids in chunk_ids:
                self._get_stats(ids, stats)
                
            if not stats:
                break # No more pairs to merge
                
            # Find the most common pair overall
            pair = max(stats, key=stats.get)
            
            idx = 256 + i
            self.merges[pair] = idx
            self.vocab[idx] = self.vocab[pair[0]] + self.vocab[pair[1]]
            
            # Apply the merge to all chunk IDs
            chunk_ids = [self._merge(ids, pair, idx) for ids in chunk_ids]
            
            if verbose:
                print(f"Merge {i+1}/{num_merges}: {pair} -> {idx} (occurrences: {stats[pair]})")

    def encode(self, text: str) -> List[int]:
        """
        Convert a string into token IDs using pre-tokenization and merges.
        """
        # 1. Pre-tokenize the text
        chunks = re.findall(self.pat, text)
        
        out_tokens = []
        # 2. Process each chunk independently
        for chunk in chunks:
            tokens = list(chunk.encode("utf-8"))
            while len(tokens) >= 2:
                stats = self._get_stats(tokens)
                pair = min(stats.keys(), key=lambda p: self.merges.get(p, float("inf")))
                if pair not in self.merges:
                    break
                idx = self.merges[pair]
                tokens = self._merge(tokens, pair, idx)
            out_tokens.extend(tokens)
            
        return out_tokens

    def decode(self, ids: List[int]) -> str:
        """
        Convert a list of token IDs back into a string.
        """
        tokens = b"".join(self.vocab[idx] for idx in ids)
        return tokens.decode("utf-8", errors="replace")

    def save_model(self, filepath: str):
        """Save the learned merges to a JSON file."""
        data = {
            "merges": {f"{p[0]},{p[1]}": idx for p, idx in self.merges.items()}
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
            
    def load_model(self, filepath: str):
        """Load learned merges from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
            
        self.merges = {}
        self.vocab = {idx: bytes([idx]) for idx in range(256)}
        
        for pair_str, idx in data["merges"].items():
            p0, p1 = map(int, pair_str.split(","))
            self.merges[(p0, p1)] = idx
            self.vocab[idx] = self.vocab[p0] + self.vocab[p1]

if __name__ == "__main__":
    text_corpus = "Hello, world! Hello there. Hello, universe. This is a small test of the tokenizer. Tokenizer test."
    print("--- Training Tokenizer ---")
    tokenizer = BPETokenizer()
    tokenizer.train(text_corpus, vocab_size=276, verbose=True)
    
    test_string = "Hello, world! testing..."
    print(f"\n--- Encoding Test ---")
    print(f"Original Text: {test_string}")
    encoded_ids = tokenizer.encode(test_string)
    print(f"Encoded IDs: {encoded_ids}")
    decoded_text = tokenizer.decode(encoded_ids)
    print(f"Decoded Text: {decoded_text}")
    assert test_string == decoded_text, "Decode(Encode(text)) must equal text!"
    print("\nSuccess! The tokenizer successfully encoded and decoded the text.")
