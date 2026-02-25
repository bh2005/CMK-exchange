import redis
import json
import argparse
from tabulate import tabulate
from datetime import datetime
import pytz

def parse_arguments():
    """Parst Kommandozeilenargumente für die Datenbanknummer."""
    parser = argparse.ArgumentParser(description="Listet den Inhalt einer Redis-Datenbank.")
    parser.add_argument(
        '-db', '--database',
        type=int,
        default=0,
        help='Redis-Datenbanknummer (z. B. 0 für db0, 1 für db1). Standard: 0'
    )
    return parser.parse_args()

def connect_to_redis(db):
    """Stellt eine Verbindung zur Redis-Datenbank her."""
    try:
        # Verbindung zu Redis auf localhost:6379, angegebene DB
        # Passe password='<dein_passwort>' an, falls in /etc/redis/redis.conf gesetzt
        client = redis.Redis(host='localhost', port=6379, db=db, decode_responses=True)
        # Teste die Verbindung
        client.ping()
        return client
    except redis.RedisError as e:
        print(f"Fehler bei der Verbindung zu Redis (DB {db}): {e}")
        exit(1)

def get_redis_contents(client):
    """Ruft alle Keys, Typen und Werte aus der Redis-Datenbank ab."""
    try:
        # Hole alle Keys mit dem Muster '*' (alle Keys)
        keys = client.keys('*')
        if not keys:
            return []

        contents = []
        for key in sorted(keys):
            key_type = client.type(key)
            value = None

            # Wert basierend auf Datentyp abrufen
            if key_type == 'string':
                value = client.get(key)
            elif key_type == 'list':
                value = client.lrange(key, 0, -1)
                value = ', '.join(value) if value else '[]'
            elif key_type == 'set':
                value = client.smembers(key)
                value = ', '.join(value) if value else '{}'
            elif key_type == 'zset':
                value = client.zrange(key, 0, -1, withscores=True)
                value = ', '.join([f"{v} ({s})" for v, s in value]) if value else '{}'
            elif key_type == 'hash':
                value = client.hgetall(key)
                value = json.dumps(value, ensure_ascii=False) if value else '{}'
            else:
                value = f'(Unbekannter Typ: {key_type})'

            contents.append([key, key_type, value])
        return contents
    except redis.RedisError as e:
        print(f"Fehler beim Abrufen der Daten: {e}")
        return []

def main():
    """Hauptfunktion: Verbindet zu Redis, holt Inhalte und zeigt sie als Tabelle an."""
    args = parse_arguments()
    db = args.database
    
    print(f"\nRedis DB{db} Inhalte (Stand: {datetime.now(pytz.timezone('Europe/Berlin')).strftime('%Y-%m-%d %H:%M:%S %Z')})\n")
    
    client = connect_to_redis(db)
    contents = get_redis_contents(client)
    
    if not contents:
        print(f"Datenbank db{db} ist leer.")
        return
    
    # Erstelle Tabelle mit tabulate
    headers = ["Key", "Typ", "Wert"]
    print(tabulate(contents, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    main()