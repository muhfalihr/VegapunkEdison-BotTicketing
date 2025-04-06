# 🤖 Vegapunk Edison - Bot Ticketing

**Vegapunk Edison** is an advanced Telegram bot-based ticketing system built to simplify and automate internal support or customer service via Telegram. It supports multilingual interactions, database integration, and is fully containerized for easy deployment.

---

## 🗂️ Repository Structure

```
.
├── deployment/
│   ├── docker/
│   ├── helm/
│   └── manifest/
└── source/
    ├── config.yml
    ├── edison.py
    ├── main.py
    ├── requirements.txt
    └── src
        ├── controller
        ├── handlers
        ├── library
        ├── localization
        ├── templates
        ├── types
        └── utility
├── Dockerfile
└── .gitignore
```

---

## ⚙️ Configuration

Edit the `config.yml` to match your deployment environment:

```yaml
bot:
  name: Vegapunk Edison - Bot Ticketing
  lang: id  # Options: id or en

telegram:
  token: "<your-bot-token>"
  chat_id: <group-or-channel-id>
  bot_id: <bot-id>
  admin_ids:
    - <admin-telegram-id>

database:
  host: "<your-db-host>"
  port: 3306
  user: "<user>"
  password: "<your-password>"
  database: "<database>"
  tables:
    - usersv2
    - ticketsv2
    - ticket_messagesv2
    - banned_users
    - handlersv2

timezone: "Asia/Jakarta"
```

---

## 📦 Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/muhfalihr/vegapunk-edison-bot-ticketing.git
   cd vegapunk-edison-bot-ticketing
   ```

2. **Create virtual environment (optional but recommended)**  
   ```bash
   python -m venv .vegapunk
   source .vegapunk/bin/activate
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the bot**  
   ```bash
   python main.py
   ```

---

## 🐳 Docker Support

Build and run the project using Docker:

```bash
docker-compose -f deployment/docker/docker-compose.yml up --build
```

---

## ☸️ Kubernetes Deployment

Use the Kubernetes manifests under `deployment/manifest/` to deploy to your cluster.

```bash
kubectl create namespace bot-ticketing

kubectl apply -k deployment/manifest/
```

---

## 🚀 Helm Deployment

Deploy to Kubernetes with Helm:

### 🧾 Prerequisites

- Kubernetes cluster
- Helm 3+
- NFS server for volume persistence

### 📝 Example `values.yaml`

```yaml
namespace: bot-ticketing

bot:
  bot_name: Vegapunk Edison - Bot Ticketing
  lang: id

  name: vegapunk-edison-bot-ticketing
  image: vegapunk-edison-bot-ticketing
  config:
    botToken: "<your-bot-token>"
    chatId: "<group-or-channel-id>"
    botId: "<bot-id>"
    adminIds:
      - "<admin-telegram-id>"
    db:
      host: svc-vegapunk-edison-database
      user: vegapunk
      password: vegapunkbotticketing
      database: bot-ticketing

mysql:
  name: vegapunk-edison-database
  user: vegapunk
  password: vegapunkbotticketing
  database: bot-ticketing
  volume:
    server: <IP-SERVER-NFS>
    path: /path/to/mount
```

### 📦 Deploy with Helm

```bash
kubectl create namespace bot-ticketing

helm install vegapunk-edison-bot-ticketing ./deployment/helm/vegapunk-edison-bot-ticketing -n bot-ticketing
```

Upgrade:

```bash
helm upgrade vegapunk-edison-bot-ticketing ./deployment/helm/vegapunk-edison-bot-ticketing -n bot-ticketing
```

Uninstall:

```bash
helm uninstall vegapunk-edison-bot-ticketing -n bot-ticketing
```

---

## 🧾 Bot Commands

The bot supports multiple roles with different command sets:

### 👤 Client Commands
| Command   | Description |
|-----------|-------------|
| `/start`  | Start interaction with the bot and create a new support ticket. |

### 🧑‍💼 Handler Commands
| Command         | Description |
|-----------------|-------------|
| `/open`         | Claim or open a ticket to start handling the issue. |
| `/close`        | Mark the current ticket as resolved and close it. |
| `/conversation` | View the current conversation in the ticket. |
| `/history`      | Display a list of previously resolved or closed tickets. |

### 🛡️ Admin Commands
| Command      | Description |
|--------------|-------------|
| `/regist`    | Register a new handler (support agent) to the system. |
| `/deregist`  | Deregister or remove an existing handler. |
| `/handlers`  | View a list of currently registered handlers. |

---

## 📑 Features

- 🎟️ Ticketing System with Telegram interface
- 🛠️ Admin controls and chat management
- 🧠 Multilingual support (Indonesian and English)
- 🐬 MySQL database integration
- 🐳 Docker & K8s ready
- 🕐 Timezone aware (Asia/Jakarta)

---

## 🧪 Requirements

See [`requirements.txt`](./requirements.txt) for full dependency list.

---

## 🔐 Security Notes

- **Never commit your real bot token or DB credentials to public repositories.**  
- Replace sensitive values in `config.yml` with environment variables or use Kubernetes secrets.

---

## ✨ Author

**Vegapunk Edison - Bot Ticketing** maintained by [muhfalihr](https://github.com/muhfalihr).
