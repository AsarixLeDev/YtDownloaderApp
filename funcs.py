import re
import unicodedata


def sanitize_filename(input_string, strict_cleaning=False):
    # Caractères à éviter sur les systèmes d'exploitation courants
    forbidden_chars = r'[<>:"/\\|?*\x00-\x1f]'
    # Remplacer les caractères interdits par un tiret bas
    sanitized = re.sub(forbidden_chars, '_', input_string)

    if strict_cleaning:
        # Décomposer les caractères unicode en caractères ASCII s'ils existent
        sanitized = unicodedata.normalize('NFKD', sanitized).encode('ASCII', 'ignore').decode()
        # Supprimer les espaces et autres caractères non alphanumériques
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)

    # Tronquer le fichier pour s'assurer qu'il ne dépasse pas 255 caractères
    sanitized = sanitized[:255]
    # Supprimer les espaces ou les points en début et fin de chaîne
    sanitized = sanitized.strip(' .')
    # Gérer les cas de noms réservés sous Windows
    windows_reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8',
                        'COM9',
                        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    # Ajouter un tiret bas si le nom est réservé
    if sanitized.upper() in windows_reserved:
        sanitized = '_' + sanitized

    return sanitized


# Exemple d'utilisation avec l'option strict_cleaning activée
input_name = "Exemple avec des espaces et des accents éèç@#"
print("Nom de fichier original:", input_name)
print("Nom de fichier sécurisé (nettoyage strict):", sanitize_filename(input_name, strict_cleaning=True))
