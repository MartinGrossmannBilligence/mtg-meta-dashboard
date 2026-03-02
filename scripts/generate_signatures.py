import json
import collections
import os

def generate_signatures(decklists_path, output_path):
    print(f"Loading decklists from {decklists_path}...")
    with open(decklists_path, 'r', encoding='utf-8') as f:
        all_decklists = json.load(f)
    
    signatures = {}
    
    for archetype, decks in all_decklists.items():
        if not decks:
            continue
            
        card_counts = collections.Counter()
        num_decks = len(decks)
        
        for deck in decks:
            # We only care about card names for the signature
            # Usually maindeck cards are most representative
            seen_in_deck = set()
            for card in deck.get('cards', []):
                card_name = card.get('name')
                if card_name:
                    seen_in_deck.add(card_name)
            
            for card_name in seen_in_deck:
                card_counts[card_name] += 1
        
        # A card is part of the signature if it appears in > 40% of decks
        # We also want to exclude basic lands likely, or at least focus on core cards
        basic_lands = {"Forest", "Island", "Mountain", "Plains", "Swamp", "Snow-Covered Forest", "Snow-Covered Island", "Snow-Covered Mountain", "Snow-Covered Plains", "Snow-Covered Swamp"}
        
        signature = [
            card for card, count in card_counts.items() 
            if (count / num_decks) >= 0.4 and card not in basic_lands
        ]
        
        signatures[archetype] = {
            "num_decks": num_decks,
            "core_cards": signature
        }
        
    print(f"Generated signatures for {len(signatures)} archetypes.")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(signatures, f, indent=2)
    print(f"Saved signatures to {output_path}")

if __name__ == "__main__":
    generate_signatures('data/decklists.json', 'data/archetype_signatures.json')
