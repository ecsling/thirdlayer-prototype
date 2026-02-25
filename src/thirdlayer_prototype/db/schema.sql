-- ThirdLayer Prototype: SQLite schema for action transitions

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_signature TEXT NOT NULL,
    action_json TEXT NOT NULL,
    timestamp REAL NOT NULL,
    url TEXT,
    success INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transitions_first_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_action TEXT NOT NULL,
    to_action TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    UNIQUE(from_action, to_action)
);

CREATE TABLE IF NOT EXISTS transitions_second_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_action_1 TEXT NOT NULL,
    from_action_2 TEXT NOT NULL,
    to_action TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    UNIQUE(from_action_1, from_action_2, to_action)
);

CREATE INDEX IF NOT EXISTS idx_transitions_first_from ON transitions_first_order(from_action);
CREATE INDEX IF NOT EXISTS idx_transitions_second_from ON transitions_second_order(from_action_1, from_action_2);
CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp);
