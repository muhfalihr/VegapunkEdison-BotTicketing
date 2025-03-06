CREATE_TABLE_TICKETS: str = """
CREATE TABLE IF NOT EXISTS ticketsv2 (
    ticket_id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(255) NOT NULL,
    issue TEXT NOT NULL,
    status ENUM('open', 'closed', 'in_progress') DEFAULT 'open',
    handler_id BIGINT NULL,
    handler_username VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_handler_id (handler_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_TICKET_MESSAGES: str = """
CREATE TABLE IF NOT EXISTS ticket_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES ticketsv2(ticket_id) ON DELETE CASCADE,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_BANNED_USERS: str = """
CREATE TABLE IF NOT EXISTS banned_users (
    user_id BIGINT PRIMARY KEY,
    reason TEXT,
    banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    banned_by BIGINT NULL,
    INDEX idx_banned_at (banned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_HANDLERS: str = """
CREATE TABLE IF NOT EXISTS handlers (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    total_tickets_handled INT DEFAULT 0,
    last_activity TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

GET_ALL_TABLES: str = """
SELECT TABLE_NAME 
FROM information_schema.tables 
WHERE TABLE_SCHEMA = %s;
"""

INSERT_USER_FOR_HANDLER: str = """
INSERT IGNORE INTO handlers (user_id, username) VALUES (%s, %s)
"""

GET_ALL_HANDLERS: str = """
SELECT * FROM handlers
"""

CHECK_USER_IS_HANDLER: str = """
SELECT COUNT(*) FROM handlers WHERE user_id = %s
"""

CREATE_TICKET: str = """
INSERT INTO ticketsv2 (ticket_id, user_id, username, issue, created_at, status) 
VALUES (%s, %s, %s, %s, %s, 'open')
"""

ADDED_TICKET_MESSAGE: str = """
INSERT INTO ticket_messages (ticket_id, user_id, username, message, timestamp) 
VALUES (%s, %s, %s, %s, %s)
"""

GET_TICKET_BY_ID: str = """
SELECT * FROM ticketsv2 WHERE ticket_id = %s
"""

CLOSED_TICKET: str = """
UPDATE ticketsv2 
SET status = 'closed', handler_id = %s, handler_username = %s, closed_at = %s 
WHERE ticket_id = %s AND status = 'open'
"""

GET_USER_TICKETS: str = """
SELECT ticket_id, issue, status, created_at, closed_at, handler_username 
FROM ticketsv2 
WHERE user_id = %s AND status = 'open'
ORDER BY created_at DESC
"""

GET_CLOSED_TICKETS: str = """
SELECT ticket_id, issue, handler_username, created_at, closed_at 
FROM ticketsv2 
WHERE user_id = %s AND status = 'closed'
ORDER BY closed_at DESC
"""

GET_OPENED_TICKETS: str = """
SELECT ticket_id, issue, handler_username, created_at 
FROM ticketsv2 
WHERE status = 'open'
ORDER BY closed_at DESC
"""
