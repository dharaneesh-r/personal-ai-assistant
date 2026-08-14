import pytest
import os
import tempfile
from app.tokenizer import BPETokenizer

def test_tokenizer_encode_decode():
    tokenizer = BPETokenizer()
    
    # Train on a small corpus
    corpus = "Hello world! This is a test. Testing the tokenizer. Hello."
    tokenizer.train(corpus, vocab_size=270, verbose=False)
    
    # Test encoding and decoding
    test_cases = [
        "Hello world!",
        "Testing the tokenizer.",
        "Unknown words like xylophone.",
        "Punctuation !?@#"
    ]
    
    for text in test_cases:
        encoded = tokenizer.encode(text)
        decoded = tokenizer.decode(encoded)
        assert decoded == text, f"Failed on '{text}': got '{decoded}'"
        
def test_tokenizer_save_load():
    tokenizer1 = BPETokenizer()
    corpus = "A quick brown fox jumps over the lazy dog."
    tokenizer1.train(corpus, vocab_size=280, verbose=False)
    
    # Save the model to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        temp_path = tmp.name
        
    try:
        tokenizer1.save_model(temp_path)
        
        # Load into a new tokenizer instance
        tokenizer2 = BPETokenizer()
        tokenizer2.load_model(temp_path)
        
        # Ensure vocabularies and merges match
        assert tokenizer1.merges == tokenizer2.merges
        assert tokenizer1.vocab == tokenizer2.vocab
        
        # Verify they encode identically
        text = "brown fox"
        assert tokenizer1.encode(text) == tokenizer2.encode(text)
    finally:
        os.remove(temp_path)
