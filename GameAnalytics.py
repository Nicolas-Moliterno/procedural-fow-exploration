import pandas as pd
import os

class GameAnalytics:
    def __init__(self, match_id, agent="unknown"):
        self.match_id = match_id
        self.agent = agent
        self.events = []
        self.positions = []
        self.actions = []
        self.step = 0
        self.enemies_killed = 0

    def log_event(self, event_type, x=None, y=None, extra=None):
        self.events.append({
            "match_id": self.match_id,
            "step": self.step,
            "type": event_type,
            "x": x,
            "y": y,
            "extra": extra
        })

    def log_position(self, entity, x, y):
        self.positions.append({
            "match_id": self.match_id,
            "step": self.step,
            "entity": entity,
            "x": x,
            "y": y
        })

    def log_action(self, action):
        self.actions.append({
            "match_id": self.match_id,
            "step": self.step,
            "action": action
        })

    def next_step(self):
        self.step += 1

    def save(self, outdir, win, score, hp_final):
        os.makedirs(outdir, exist_ok=True)

        # ------------------------
        # MATCH SUMMARY
        # ------------------------
        summary = pd.DataFrame([{
            "match_id": self.match_id,
            "agent": self.agent,
            "steps": int(self.step),
            "win": bool(win),
            "score": int(score),
            "hp_final": int(hp_final),
            "enemies_killed": int(self.enemies_killed)
        }])

        matches_path = os.path.join(outdir, "matches.csv")

        if not os.path.exists(matches_path):
            summary.to_csv(matches_path, index=False)
        else:
            summary.to_csv(matches_path, mode="a", header=False, index=False)

        # ------------------------
        # EVENTS
        # ------------------------
        if self.events:
            events_df = pd.DataFrame(self.events)
            events_path = os.path.join(outdir, "events.csv")

            if not os.path.exists(events_path):
                events_df.to_csv(events_path, index=False)
            else:
                events_df.to_csv(events_path, mode="a", header=False, index=False)

        # ------------------------
        # POSITIONS
        # ------------------------
        if self.positions:
            positions_df = pd.DataFrame(self.positions)
            positions_path = os.path.join(outdir, "positions.csv")

            if not os.path.exists(positions_path):
                positions_df.to_csv(positions_path, index=False)
            else:
                positions_df.to_csv(positions_path, mode="a", header=False, index=False)

        # ------------------------
        # ACTIONS
        # ------------------------
        if self.actions:
            actions_df = pd.DataFrame(self.actions)
            actions_path = os.path.join(outdir, "actions.csv")

            if not os.path.exists(actions_path):
                actions_df.to_csv(actions_path, index=False)
            else:
                actions_df.to_csv(actions_path, mode="a", header=False, index=False)
