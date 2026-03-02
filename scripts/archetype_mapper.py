import json
import os

class ArchetypeMapper:
    def __init__(self, signatures_path):
        with open(signatures_path, 'r', encoding='utf-8') as f:
            self.signatures = json.load(f)
            
    def map_deck(self, mainboard_cards):
        """
        Maps a list of card names to the best-fitting archetype using Jaccard similarity.
        mainboard_cards: list of strings (card names)
        """
        if not mainboard_cards:
            return "Unknown", 0.0
            
        deck_set = set(mainboard_cards)
        best_match = "Unknown"
        max_similarity = 0.0
        
        for archetype, data in self.signatures.items():
            sig_set = set(data.get("core_cards", []))
            if not sig_set:
                continue
                
            intersection = len(deck_set.intersection(sig_set))
            union = len(deck_set.union(sig_set))
            
            similarity = intersection / union if union > 0 else 0
            
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = archetype
                
        return best_match, max_similarity

    def map_by_name(self, spicerack_name):
        """Attempts to map by name similarity first."""
        # Simple exact match or subset match
        name_lower = spicerack_name.lower()
        for archetype in self.signatures.keys():
            if archetype.lower() in name_lower or name_lower in archetype.lower():
                return archetype
        return None

if __name__ == "__main__":
    # Quick test
    mapper = ArchetypeMapper('data/archetype_signatures.json')
    
    # Test with cards for "Goblins" (typical cards)
    goblins_test = ["Goblin Lackey", "Goblin Matron", "Goblin Ringleader", "Goblin Piledriver", "Siege-Gang Commander"]
    match, score = mapper.map_deck(goblins_test)
    print(f"Goblins test match: {match} (Score: {score:.4f})")
    
    # Test with cards for "Stiflenought"
    stifle_test = ["Stifle", "Phyrexian Dreadnought", "Vision Charm", "Force of Will", "Daze"]
    match, score = mapper.map_deck(stifle_test)
    print(f"Stiflenought test match: {match} (Score: {score:.4f})")
