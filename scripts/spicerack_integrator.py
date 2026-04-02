import json
import os
import time
from moxfield_api import MoxfieldAPI
from archetype_mapper import ArchetypeMapper

class SpicerackIntegrator:
    def __init__(self, spicerack_dump_path, signatures_path):
        self.spicerack_data = []
        if os.path.exists(spicerack_dump_path):
            with open(spicerack_dump_path, 'r', encoding='utf-8') as f:
                self.spicerack_data = json.load(f)
        
        self.moxfield = MoxfieldAPI()
        self.mapper = ArchetypeMapper(signatures_path)
        self.output_path = 'data/spicerack_mapped.json'

    def process(self, limit=None):
        results = []
        count = 0
        
        print(f"Processing {len(self.spicerack_data)} tournaments from Spicerack...")
        
        for tournament in self.spicerack_data:
            t_name = tournament.get('tournamentName', 'Unknown Tournament')
            print(f"\nTournament: {t_name}")
            
            mapped_standings = []
            for standing in tournament.get('standings', []):
                deck_url = standing.get('decklist')
                player = standing.get('name')
                
                if not deck_url or "moxfield.com" not in deck_url:
                    mapped_standings.append({**standing, "mapped_archetype": "Unknown", "confidence": 0.0})
                    continue
                
                # print(f"  Fetching deck for {player}...")
                deck = self.moxfield.fetch_deck(deck_url)
                
                if deck:
                    mainboard_names = [c['name'] for c in deck.get('mainboard', [])]
                    archetype, confidence = self.mapper.map_deck(mainboard_names)
                    display_player = player if player else "Unknown"
                    print(f"  [OK] {display_player:<20} -> {archetype:<20} (Conf: {confidence:.2f})")
                    
                    mapped_standings.append({
                        **standing,
                        "mapped_archetype": archetype,
                        "confidence": confidence,
                        "deck_data": deck
                    })
                else:
                    print(f"  [FAIL] {player:<20} - could not reach Moxfield")
                    mapped_standings.append({**standing, "mapped_archetype": "Unknown", "confidence": 0.0})
                
                count += 1
                if limit and count >= limit: break
            
            results.append({**tournament, "standings": mapped_standings})
            if limit and count >= limit: break
                
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nSUCCESS! Processed {count} decklists. Saved to {self.output_path}")

if __name__ == "__main__":
    integrator = SpicerackIntegrator('spicerack_dump.json', 'data/archetype_signatures.json')
    # Run for all tournaments
    integrator.process()
