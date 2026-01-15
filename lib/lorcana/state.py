"""
LorcanaState - pure game state with Lorcana-specific operations.

No filesystem knowledge. Just graph + game logic.
Persistence handled separately in lib/core/persistence.py
"""
import networkx as nx
from lib.core.graph import get_node_attr
from lib.lorcana.cards import get_card_db
from lib.lorcana.helpers import ZONE_HAND


class LorcanaState:
    """
    Pure Lorcana game state - graph + decks + game operations.

    This is where ALL Lorcana game logic lives. Persistence is separate.
    """

    def __init__(self, graph: nx.MultiDiGraph, deck1_ids: list[str], deck2_ids: list[str]):
        """
        Create state from components.

        Args:
            graph: NetworkX MultiDiGraph representing game state
            deck1_ids: List of card IDs remaining in P1's deck
            deck2_ids: List of card IDs remaining in P2's deck
        """
        self.graph = graph
        self.deck1_ids = deck1_ids
        self.deck2_ids = deck2_ids

    # ========== Game Operations ==========

    def draw(self, player: int, count: int = 1):
        """
        Draw cards from deck to hand.

        Args:
            player: Player number (1 or 2)
            count: Number of cards to draw

        Mutates: graph (adds card nodes), deck_ids (removes drawn cards)
        """
        deck_ids = self.deck1_ids if player == 1 else self.deck2_ids

        # Draw cards
        for card_id in deck_ids[:count]:
            self._create_card_node(card_id, player, zone=ZONE_HAND)

        # Update deck state
        remaining = deck_ids[count:]
        if player == 1:
            self.deck1_ids = remaining
        else:
            self.deck2_ids = remaining

    def exert(self, card_node: str):
        """Set card to exerted state."""
        self.graph.nodes[card_node]['exerted'] = '1'

    def ready(self, card_node: str):
        """Set card to ready state."""
        self.graph.nodes[card_node]['exerted'] = '0'

    def add_lore(self, player: str, amount: int):
        """
        Add lore to player and check for win condition.

        Player wins immediately if they reach 20+ lore.
        """
        current = int(get_node_attr(self.graph, player, 'lore', '0'))
        new_lore = current + amount
        self.graph.nodes[player]['lore'] = str(new_lore)

        # Check win condition
        if new_lore >= 20:
            self.graph.nodes['game']['winner'] = player
            self.graph.nodes['game']['game_over'] = '1'

    def move_card(self, card_node: str, zone: str):
        """
        Move card to different zone.

        Args:
            card_node: Card node ID
            zone: Zone kind (ZONE_HAND, ZONE_PLAY, etc.)
        """
        self.graph.nodes[card_node]['zone'] = zone

    def damage_card(self, card_node: str, amount: int):
        """Deal damage to card."""
        current = int(self.graph.nodes[card_node].get('damage', 0))
        self.graph.nodes[card_node]['damage'] = str(current + amount)

    # ========== Internal Helpers ==========

    def _create_card_node(self, card_id: str, player: int, zone: str) -> str:
        """
        Create card node in graph.

        Args:
            card_id: Normalized ID like "tinker_bell_giant_fairy.a"
            player: Player number (1 or 2)
            zone: Zone kind (ZONE_HAND, ZONE_PLAY, etc.)

        Returns:
            Node ID: "p1.tinker_bell_giant_fairy.a"
        """
        card_db = get_card_db()

        # Extract base card name (remove copy suffix)
        base_name = card_id.rsplit('.', 1)[0]

        # O(1) lookup by normalized name
        card_data = card_db.get(base_name)

        if not card_data:
            raise ValueError(f"Card not found for ID: {card_id}")

        node_id = f"p{player}.{card_id}"

        self.graph.add_node(
            node_id,
            type="Card",
            card_id=card_data["id"],
            exerted="0",
            damage="0",
            label=base_name,
            zone=zone
        )

        return node_id
