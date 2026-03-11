"""DedupGenie i18n — all user-facing strings, keyed by ISO 639-1 language code.

Usage:
    from translations import LANGUAGES, get_translator
    tr = get_translator('fr')
    tr('btn_analyze')               # → 'Analyser'
    tr('status_scan_complete',      # → format with named placeholders
       total_files=42, dupe_groups=3, dupe_files=7, waste_str='12.3 MB')

Guidelines for contributors:
- Keys are snake_case English descriptors — never use source text as key.
- Use named placeholders {count}, {total}, etc. — never positional.
- Do NOT split sentences across multiple keys (breaks word order in other languages).
- Arabic is RTL; layout direction is handled in app.py, not here.
- Pluralization: use {count} in the string; complex plural forms are out of scope
  for this app's simple UI. If needed later, add a plural() helper.
"""

LANGUAGES = {
    'en': 'English',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'ar': 'العربية',
    'pt': 'Português',
}

# RTL languages — app.py checks this to set layout direction
RTL_LANGUAGES = {'ar'}

_STRINGS = {

# ======================================================================
# English (source language — canonical reference for all keys)
# ======================================================================
'en': {
    # Window
    'window_title': 'DedupGenie',

    # Target row
    'label_target': 'Target:',
    'placeholder_select_directory': 'Select a directory to scan...',
    'btn_browse': 'Browse...',
    'dialog_file_select': 'Select Directory',

    # Analysis row
    'label_sensitivity': 'Sensitivity:',
    'combo_strict': 'Strict',
    'combo_balanced': 'Balanced',
    'combo_fuzzy': 'Fuzzy',
    'tooltip_sensitivity': (
        'Strict = exact match (SHA-256)\n'
        'Balanced = fast near-exact (head+tail)\n'
        'Fuzzy = similar content (SimHash)'
    ),
    'btn_analyze': 'Analyze',

    # Global actions
    'btn_auto_clean': 'Auto-clean duplicates',
    'tooltip_auto_clean': (
        'Automatically move redundant copies to quarantine.\n'
        'Keeps the file with the shortest, cleanest path.'
    ),
    'btn_open_quarantine': 'Open quarantine folder',
    'btn_empty_quarantine': 'Empty quarantine',

    # Folder tree headers
    'tree_folder': 'Folder',
    'tree_files': 'Files',
    'tree_dupes': 'Dupes',
    'tree_size': 'Size',

    # File panel actions
    'btn_select_duplicates': 'Select duplicates',
    'tooltip_select_duplicates': 'Select all duplicate copies (keeps originals unselected)',
    'btn_deselect_all': 'Deselect all',
    'btn_quarantine_selected': 'Quarantine selected',
    'btn_delete_selected': 'Delete selected',

    # File tree headers
    'tree_filename': 'Filename',
    'tree_verdict': 'Verdict',

    # Comparison panel
    'label_comparison': 'Comparison',

    # Waste donut
    'tooltip_waste_donut': 'Duplicate waste ratio',
    'tooltip_waste_no_data': 'No data — run Analyze first',
    'tooltip_waste_detail': 'Duplicate waste: {waste} / {total} ({pct}%)',

    # Menu
    'menu_help': 'Help',
    'menu_how_it_works': 'How it works',
    'menu_about': 'About',
    'menu_language': 'Language',
    'context_open_folder': 'Open containing folder',

    # Tree item statuses
    'status_quarantine_label': 'QUARANTINE',
    'status_quarantined': 'QUARANTINED',
    'status_match': 'MATCH ({count})',
    'status_unique': 'Unique',
    'status_match_child': 'Match',

    # Comparison panel labels
    'comp_file_a': 'FILE A:',
    'comp_file_b': 'FILE B:',
    'comp_size': 'Size:',
    'comp_size_diff': 'Size difference:',
    'comp_text_sim': 'Text similarity:',
    'comp_simhash_sim': 'SimHash similarity:',
    'comp_hamming': 'Hamming distance:',
    'comp_binary': '[Binary or protected file]',

    # Status bar messages
    'status_settings_changed': 'Settings changed — re-analyze to update.',
    'status_checked': 'Checked {count} duplicate copies.',
    'status_no_dupes_to_check': 'No duplicates to check — select a folder first.',
    'status_nothing_checked': 'Nothing checked.',
    'status_quarantined_files': 'Quarantined {moved}/{total} files.',
    'status_deleted_files': 'Deleted {deleted}/{total} files.',
    'status_no_dupes_found': 'No duplicates found — run ANALYZE first.',
    'status_no_redundant': 'No redundant copies to move.',
    'status_no_quarantine': 'No quarantine folder found.',
    'status_quarantine_empty': 'Quarantine is already empty.',
    'status_scan_complete': (
        'Done: {total_files} files, {dupe_groups} duplicate groups, '
        '{dupe_files} redundant copies — {waste_str} wasted.'
    ),
    'status_wizard_moved': 'Wizard moved {moved}/{total} files to quarantine.',
    'status_purged': 'Purged {deleted}/{total} files from quarantine.',

    # Dialog titles
    'dialog_invalid_path': 'Invalid path',
    'dialog_quarantine': 'Quarantine',
    'dialog_delete': 'Permanent Delete',
    'dialog_auto_wizard': 'Smart Auto-Wizard',
    'dialog_purge': 'Purge Quarantine',

    # Dialog messages
    'msg_invalid_path': 'Directory not found:\n{path}',
    'msg_quarantine_confirm': 'Move {count} checked file(s) to quarantine?',
    'msg_delete_confirm': (
        'PERMANENTLY DELETE {count} checked file(s)?\n'
        'This cannot be undone.'
    ),
    'msg_wizard_confirm': (
        'The wizard identified {count} redundant copies.\n'
        'Move them to quarantine?\n\n'
        '(Keeps the file with the shortest, cleanest path in each group.)'
    ),
    'msg_purge_confirm': (
        'PERMANENTLY DELETE all {count} file(s) in quarantine?\n'
        'This cannot be undone.'
    ),

    # Help — How it works (HTML)
    'help_how_it_works': (
        '<h3>Quick start</h3>'
        '<ol>'
        '<li><b>Set a target directory</b> — type a path or click <i>Browse...</i></li>'
        '<li><b>Pick a sensitivity mode:</b><br>'
        '&nbsp;&nbsp;Strict — exact match (SHA-256, zero false positives)<br>'
        '&nbsp;&nbsp;Balanced — fast near-exact (compares head + tail bytes)<br>'
        '&nbsp;&nbsp;Fuzzy — finds similar content (~85%+ overlap)</li>'
        '<li><b>Click Analyze</b> — the scan runs in the background</li>'
        '<li><b>Click a folder</b> on the left to see its files on the right</li>'
        '<li><b>Click a file</b> to compare it with its duplicate in the bottom panel</li>'
        '<li><b>Clean up:</b> select duplicates, then quarantine or delete them</li>'
        '</ol>'
        '<h3>Detection pipeline</h3>'
        '<p><b>Strict &amp; Balanced</b> use a progressive pipeline:<br>'
        'file size → first 4 KB → last 4 KB → full SHA-256 (Strict only).<br>'
        'Each stage eliminates non-candidates before reading more data.</p>'
        '<p><b>Fuzzy</b> tokenizes text (or uses byte n-grams for binary files), '
        'computes a 64-bit SimHash, and splits it into 8 LSH bands. '
        'Files sharing any band are flagged as similar.</p>'
        '<h3>Quarantine</h3>'
        '<p>Files are never deleted directly — they are first moved to a '
        '<code>_FORENSIC_QUARANTINE</code> folder inside the target directory. '
        'You can review them, restore them manually, or use <i>Empty quarantine</i> '
        'to permanently delete them.</p>'
        '<h3>Auto-clean</h3>'
        '<p>The auto-clean wizard picks which copy to keep using heuristics: '
        "shortest path, absence of keywords like 'copy' or 'backup', "
        'and most recent modification time as a tiebreaker. '
        'All other copies are moved to quarantine.</p>'
        '<h3>Safety &amp; disclaimer</h3>'
        '<p><b>Back up your data before using this tool.</b> While multiple '
        'safeguards are in place — confirmation dialogs, quarantine step before '
        'deletion, and no files are ever deleted without explicit user action — '
        'no software is infallible.</p>'
        "<p>Deleted files may still be recoverable from your operating system's "
        'trash/recycle bin depending on your platform and configuration.</p>'
        '<p>This software is provided as-is, without warranty of any kind. '
        'The authors are not liable for any data loss. '
        '<b>You use this tool entirely at your own risk.</b></p>'
    ),

    # Help — About (HTML)
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>Version 1.0.0</p>'
        '<p>Duplicate file finder with forensic-grade detection.</p>'
        '<p>Algorithms: SHA-256, progressive head/tail pipeline, '
        'SimHash + LSH banding.</p>'
        '<p>Built with Python and PyQt5.</p>'
        '<hr>'
        '<p><b>Install:</b> <code>pip install dedupgenie</code><br>'
        '<b>Run:</b> <code>dedupgenie</code><br>'
        '<b>PyPI:</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub:</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>Created by <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'with <b>Gemini</b> and <b>Claude</b>.</p>'
    ),
},

# ======================================================================
# Français
# ======================================================================
'fr': {
    'window_title': 'DedupGenie',
    'label_target': 'Cible :',
    'placeholder_select_directory': 'Sélectionnez un dossier à analyser...',
    'btn_browse': 'Parcourir...',
    'dialog_file_select': 'Sélectionner un dossier',
    'label_sensitivity': 'Sensibilité :',
    'combo_strict': 'Strict',
    'combo_balanced': 'Équilibré',
    'combo_fuzzy': 'Flou',
    'tooltip_sensitivity': (
        'Strict = correspondance exacte (SHA-256)\n'
        'Équilibré = quasi-exact rapide (début+fin)\n'
        'Flou = contenu similaire (SimHash)'
    ),
    'btn_analyze': 'Analyser',
    'btn_auto_clean': 'Nettoyage auto des doublons',
    'tooltip_auto_clean': (
        'Déplace automatiquement les copies redondantes en quarantaine.\n'
        'Conserve le fichier au chemin le plus court et propre.'
    ),
    'btn_open_quarantine': 'Ouvrir le dossier de quarantaine',
    'btn_empty_quarantine': 'Vider la quarantaine',
    'tree_folder': 'Dossier',
    'tree_files': 'Fichiers',
    'tree_dupes': 'Doublons',
    'tree_size': 'Taille',
    'btn_select_duplicates': 'Sélectionner les doublons',
    'tooltip_select_duplicates': 'Sélectionner toutes les copies (les originaux restent décochés)',
    'btn_deselect_all': 'Tout décocher',
    'btn_quarantine_selected': 'Quarantaine sélectionnés',
    'btn_delete_selected': 'Supprimer sélectionnés',
    'tree_filename': 'Nom de fichier',
    'tree_verdict': 'Verdict',
    'label_comparison': 'Comparaison',
    'tooltip_waste_donut': "Ratio d'espace gaspillé",
    'tooltip_waste_no_data': 'Aucune donnée — lancez Analyser',
    'tooltip_waste_detail': 'Espace gaspillé : {waste} / {total} ({pct} %)',
    'menu_help': 'Aide',
    'menu_how_it_works': 'Fonctionnement',
    'menu_about': 'À propos',
    'menu_language': 'Langue',
    'context_open_folder': 'Ouvrir le dossier parent',
    'status_quarantine_label': 'QUARANTAINE',
    'status_quarantined': 'EN QUARANTAINE',
    'status_match': 'DOUBLON ({count})',
    'status_unique': 'Unique',
    'status_match_child': 'Doublon',
    'comp_file_a': 'FICHIER A :',
    'comp_file_b': 'FICHIER B :',
    'comp_size': 'Taille :',
    'comp_size_diff': 'Différence de taille :',
    'comp_text_sim': 'Similarité textuelle :',
    'comp_simhash_sim': 'Similarité SimHash :',
    'comp_hamming': 'Distance de Hamming :',
    'comp_binary': '[Fichier binaire ou protégé]',
    'status_settings_changed': "Paramètres modifiés — relancez l'analyse.",
    'status_checked': '{count} copies cochées.',
    'status_no_dupes_to_check': 'Aucun doublon à cocher — sélectionnez un dossier.',
    'status_nothing_checked': 'Rien de coché.',
    'status_quarantined_files': '{moved}/{total} fichiers mis en quarantaine.',
    'status_deleted_files': '{deleted}/{total} fichiers supprimés.',
    'status_no_dupes_found': 'Aucun doublon trouvé — lancez ANALYSER.',
    'status_no_redundant': 'Aucune copie redondante à déplacer.',
    'status_no_quarantine': 'Aucun dossier de quarantaine trouvé.',
    'status_quarantine_empty': 'La quarantaine est déjà vide.',
    'status_scan_complete': (
        'Terminé : {total_files} fichiers, {dupe_groups} groupes de doublons, '
        '{dupe_files} copies redondantes — {waste_str} gaspillés.'
    ),
    'status_wizard_moved': "L'assistant a déplacé {moved}/{total} fichiers en quarantaine.",
    'status_purged': '{deleted}/{total} fichiers purgés de la quarantaine.',
    'dialog_invalid_path': 'Chemin invalide',
    'dialog_quarantine': 'Quarantaine',
    'dialog_delete': 'Suppression définitive',
    'dialog_auto_wizard': 'Assistant de nettoyage',
    'dialog_purge': 'Purger la quarantaine',
    'msg_invalid_path': 'Dossier introuvable :\n{path}',
    'msg_quarantine_confirm': 'Déplacer {count} fichier(s) cochés en quarantaine ?',
    'msg_delete_confirm': (
        'SUPPRIMER DÉFINITIVEMENT {count} fichier(s) cochés ?\n'
        'Cette action est irréversible.'
    ),
    'msg_wizard_confirm': (
        "L'assistant a identifié {count} copies redondantes.\n"
        'Les déplacer en quarantaine ?\n\n'
        '(Conserve le fichier au chemin le plus court et propre dans chaque groupe.)'
    ),
    'msg_purge_confirm': (
        'SUPPRIMER DÉFINITIVEMENT les {count} fichier(s) en quarantaine ?\n'
        'Cette action est irréversible.'
    ),
    'help_how_it_works': (
        '<h3>Démarrage rapide</h3>'
        '<ol>'
        '<li><b>Choisissez un dossier cible</b> — tapez un chemin ou cliquez sur <i>Parcourir...</i></li>'
        '<li><b>Choisissez un mode de sensibilité :</b><br>'
        '&nbsp;&nbsp;Strict — correspondance exacte (SHA-256, zéro faux positif)<br>'
        '&nbsp;&nbsp;Équilibré — quasi-exact rapide (compare début + fin du fichier)<br>'
        '&nbsp;&nbsp;Flou — trouve le contenu similaire (~85 %+ de ressemblance)</li>'
        "<li><b>Cliquez sur Analyser</b> — l'analyse s'exécute en arrière-plan</li>"
        '<li><b>Cliquez sur un dossier</b> à gauche pour voir ses fichiers à droite</li>'
        '<li><b>Cliquez sur un fichier</b> pour le comparer avec son doublon dans le panneau du bas</li>'
        '<li><b>Nettoyez :</b> sélectionnez les doublons, puis mettez-les en quarantaine ou supprimez-les</li>'
        '</ol>'
        '<h3>Pipeline de détection</h3>'
        '<p><b>Strict et Équilibré</b> utilisent un pipeline progressif :<br>'
        'taille du fichier → premiers 4 Ko → derniers 4 Ko → SHA-256 complet (Strict uniquement).<br>'
        'Chaque étape élimine les non-candidats avant de lire plus de données.</p>'
        "<p><b>Flou</b> tokenise le texte (ou utilise des n-grammes d'octets pour les binaires), "
        'calcule un SimHash 64 bits et le divise en 8 bandes LSH. '
        'Les fichiers partageant une bande sont signalés comme similaires.</p>'
        '<h3>Quarantaine</h3>'
        "<p>Les fichiers ne sont jamais supprimés directement — ils sont d'abord déplacés "
        "dans un dossier <code>_FORENSIC_QUARANTINE</code> à l'intérieur du dossier cible. "
        'Vous pouvez les examiner, les restaurer manuellement, ou utiliser '
        '<i>Vider la quarantaine</i> pour les supprimer définitivement.</p>'
        '<h3>Nettoyage automatique</h3>'
        "<p>L'assistant choisit quelle copie conserver selon des heuristiques : "
        'chemin le plus court, absence de mots-clés comme « copie » ou « backup », '
        "et date de modification la plus récente en cas d'égalité. "
        'Toutes les autres copies sont mises en quarantaine.</p>'
        '<h3>Sécurité et avertissement</h3>'
        "<p><b>Sauvegardez vos données avant d'utiliser cet outil.</b> Bien que plusieurs "
        'protections soient en place — boîtes de confirmation, étape de quarantaine avant '
        "suppression, et aucun fichier n'est supprimé sans action explicite — "
        "aucun logiciel n'est infaillible.</p>"
        '<p>Les fichiers supprimés peuvent encore être récupérables depuis la corbeille '
        "de votre système d'exploitation selon votre plateforme et configuration.</p>"
        "<p>Ce logiciel est fourni tel quel, sans garantie d'aucune sorte. "
        'Les auteurs ne sont pas responsables de toute perte de données. '
        '<b>Vous utilisez cet outil entièrement à vos risques et périls.</b></p>'
    ),
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>Version 1.0.0</p>'
        '<p>Outil de détection de fichiers en double de qualité forensique.</p>'
        '<p>Algorithmes : SHA-256, pipeline progressif début/fin, '
        'SimHash + bandes LSH.</p>'
        '<p>Construit avec Python et PyQt5.</p>'
        '<hr>'
        '<p><b>Installer :</b> <code>pip install dedupgenie</code><br>'
        '<b>Lancer :</b> <code>dedupgenie</code><br>'
        '<b>PyPI :</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub :</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>Créé par <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'avec <b>Gemini</b> et <b>Claude</b>.</p>'
    ),
},

# ======================================================================
# Deutsch
# ======================================================================
'de': {
    'window_title': 'DedupGenie',
    'label_target': 'Zielordner:',
    'placeholder_select_directory': 'Ordner zum Scannen auswählen...',
    'btn_browse': 'Durchsuchen...',
    'dialog_file_select': 'Ordner auswählen',
    'label_sensitivity': 'Empfindlichkeit:',
    'combo_strict': 'Strikt',
    'combo_balanced': 'Ausgewogen',
    'combo_fuzzy': 'Unscharf',
    'tooltip_sensitivity': (
        'Strikt = exakte Übereinstimmung (SHA-256)\n'
        'Ausgewogen = schnell, fast exakt (Anfang+Ende)\n'
        'Unscharf = ähnlicher Inhalt (SimHash)'
    ),
    'btn_analyze': 'Analysieren',
    'btn_auto_clean': 'Duplikate automatisch bereinigen',
    'tooltip_auto_clean': (
        'Verschiebt überflüssige Kopien automatisch in die Quarantäne.\n'
        'Behält die Datei mit dem kürzesten, saubersten Pfad.'
    ),
    'btn_open_quarantine': 'Quarantäne-Ordner öffnen',
    'btn_empty_quarantine': 'Quarantäne leeren',
    'tree_folder': 'Ordner',
    'tree_files': 'Dateien',
    'tree_dupes': 'Duplikate',
    'tree_size': 'Größe',
    'btn_select_duplicates': 'Duplikate auswählen',
    'tooltip_select_duplicates': 'Alle Duplikatkopien auswählen (Originale bleiben abgewählt)',
    'btn_deselect_all': 'Alle abwählen',
    'btn_quarantine_selected': 'Ausgewählte in Quarantäne',
    'btn_delete_selected': 'Ausgewählte löschen',
    'tree_filename': 'Dateiname',
    'tree_verdict': 'Ergebnis',
    'label_comparison': 'Vergleich',
    'tooltip_waste_donut': 'Verschwendungsquote durch Duplikate',
    'tooltip_waste_no_data': 'Keine Daten — zuerst Analysieren starten',
    'tooltip_waste_detail': 'Duplikat-Verschwendung: {waste} / {total} ({pct} %)',
    'menu_help': 'Hilfe',
    'menu_how_it_works': 'So funktioniert es',
    'menu_about': 'Über',
    'menu_language': 'Sprache',
    'context_open_folder': 'Übergeordneten Ordner öffnen',
    'status_quarantine_label': 'QUARANTÄNE',
    'status_quarantined': 'IN QUARANTÄNE',
    'status_match': 'DUPLIKAT ({count})',
    'status_unique': 'Einzigartig',
    'status_match_child': 'Duplikat',
    'comp_file_a': 'DATEI A:',
    'comp_file_b': 'DATEI B:',
    'comp_size': 'Größe:',
    'comp_size_diff': 'Größenunterschied:',
    'comp_text_sim': 'Textähnlichkeit:',
    'comp_simhash_sim': 'SimHash-Ähnlichkeit:',
    'comp_hamming': 'Hamming-Distanz:',
    'comp_binary': '[Binärdatei oder geschützte Datei]',
    'status_settings_changed': 'Einstellungen geändert — erneut analysieren.',
    'status_checked': '{count} Duplikatkopien markiert.',
    'status_no_dupes_to_check': 'Keine Duplikate zum Markieren — wählen Sie zuerst einen Ordner.',
    'status_nothing_checked': 'Nichts markiert.',
    'status_quarantined_files': '{moved}/{total} Dateien in Quarantäne verschoben.',
    'status_deleted_files': '{deleted}/{total} Dateien gelöscht.',
    'status_no_dupes_found': 'Keine Duplikate gefunden — starten Sie ANALYSIEREN.',
    'status_no_redundant': 'Keine überflüssigen Kopien zu verschieben.',
    'status_no_quarantine': 'Kein Quarantäne-Ordner gefunden.',
    'status_quarantine_empty': 'Quarantäne ist bereits leer.',
    'status_scan_complete': (
        'Fertig: {total_files} Dateien, {dupe_groups} Duplikatgruppen, '
        '{dupe_files} überflüssige Kopien — {waste_str} verschwendet.'
    ),
    'status_wizard_moved': 'Assistent hat {moved}/{total} Dateien in Quarantäne verschoben.',
    'status_purged': '{deleted}/{total} Dateien aus Quarantäne gelöscht.',
    'dialog_invalid_path': 'Ungültiger Pfad',
    'dialog_quarantine': 'Quarantäne',
    'dialog_delete': 'Endgültig löschen',
    'dialog_auto_wizard': 'Intelligenter Assistent',
    'dialog_purge': 'Quarantäne leeren',
    'msg_invalid_path': 'Ordner nicht gefunden:\n{path}',
    'msg_quarantine_confirm': '{count} markierte Datei(en) in Quarantäne verschieben?',
    'msg_delete_confirm': (
        '{count} markierte Datei(en) ENDGÜLTIG LÖSCHEN?\n'
        'Dies kann nicht rückgängig gemacht werden.'
    ),
    'msg_wizard_confirm': (
        'Der Assistent hat {count} überflüssige Kopien identifiziert.\n'
        'In Quarantäne verschieben?\n\n'
        '(Behält die Datei mit dem kürzesten, saubersten Pfad in jeder Gruppe.)'
    ),
    'msg_purge_confirm': (
        'Alle {count} Datei(en) in der Quarantäne ENDGÜLTIG LÖSCHEN?\n'
        'Dies kann nicht rückgängig gemacht werden.'
    ),
    'help_how_it_works': (
        '<h3>Schnellstart</h3>'
        '<ol>'
        '<li><b>Zielordner festlegen</b> — Pfad eingeben oder <i>Durchsuchen...</i> klicken</li>'
        '<li><b>Empfindlichkeit wählen:</b><br>'
        '&nbsp;&nbsp;Strikt — exakte Übereinstimmung (SHA-256, keine Fehlalarme)<br>'
        '&nbsp;&nbsp;Ausgewogen — schnell, fast exakt (vergleicht Anfang + Ende)<br>'
        '&nbsp;&nbsp;Unscharf — findet ähnliche Inhalte (~85 %+ Überlappung)</li>'
        '<li><b>Analysieren klicken</b> — der Scan läuft im Hintergrund</li>'
        '<li><b>Ordner anklicken</b> (links), um Dateien anzuzeigen (rechts)</li>'
        '<li><b>Datei anklicken</b>, um sie im unteren Bereich zu vergleichen</li>'
        '<li><b>Bereinigen:</b> Duplikate auswählen, dann in Quarantäne verschieben oder löschen</li>'
        '</ol>'
        '<h3>Erkennungs-Pipeline</h3>'
        '<p><b>Strikt und Ausgewogen</b> nutzen eine progressive Pipeline:<br>'
        'Dateigröße → erste 4 KB → letzte 4 KB → vollständiger SHA-256 (nur Strikt).<br>'
        'Jede Stufe eliminiert Nicht-Kandidaten, bevor mehr Daten gelesen werden.</p>'
        '<p><b>Unscharf</b> tokenisiert Text (oder nutzt Byte-N-Gramme für Binärdateien), '
        'berechnet einen 64-Bit-SimHash und teilt ihn in 8 LSH-Bänder. '
        'Dateien, die ein Band teilen, werden als ähnlich markiert.</p>'
        '<h3>Quarantäne</h3>'
        '<p>Dateien werden nie direkt gelöscht — sie werden zuerst in einen '
        '<code>_FORENSIC_QUARANTINE</code>-Ordner innerhalb des Zielordners verschoben. '
        'Sie können sie prüfen, manuell wiederherstellen oder mit '
        '<i>Quarantäne leeren</i> endgültig löschen.</p>'
        '<h3>Automatische Bereinigung</h3>'
        '<p>Der Assistent wählt anhand von Heuristiken, welche Kopie behalten wird: '
        "kürzester Pfad, Fehlen von Schlüsselwörtern wie 'copy' oder 'backup', "
        'und neuestes Änderungsdatum als Tiebreaker. '
        'Alle anderen Kopien werden in Quarantäne verschoben.</p>'
        '<h3>Sicherheit &amp; Haftungsausschluss</h3>'
        '<p><b>Sichern Sie Ihre Daten, bevor Sie dieses Tool verwenden.</b> Obwohl mehrere '
        'Schutzmaßnahmen vorhanden sind — Bestätigungsdialoge, Quarantäneschritt vor '
        'dem Löschen, und keine Datei wird ohne ausdrückliche Benutzeraktion gelöscht — '
        'ist keine Software unfehlbar.</p>'
        '<p>Gelöschte Dateien können je nach Plattform und Konfiguration '
        'aus dem Papierkorb wiederhergestellt werden.</p>'
        '<p>Diese Software wird ohne Gewähr bereitgestellt. '
        'Die Autoren haften nicht für Datenverlust. '
        '<b>Die Nutzung erfolgt auf eigenes Risiko.</b></p>'
    ),
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>Version 1.0.0</p>'
        '<p>Duplikat-Finder mit forensischer Erkennung.</p>'
        '<p>Algorithmen: SHA-256, progressiver Anfang/Ende-Pipeline, '
        'SimHash + LSH-Bänder.</p>'
        '<p>Erstellt mit Python und PyQt5.</p>'
        '<hr>'
        '<p><b>Installieren:</b> <code>pip install dedupgenie</code><br>'
        '<b>Starten:</b> <code>dedupgenie</code><br>'
        '<b>PyPI:</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub:</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>Erstellt von <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'mit <b>Gemini</b> und <b>Claude</b>.</p>'
    ),
},

# ======================================================================
# Italiano
# ======================================================================
'it': {
    'window_title': 'DedupGenie',
    'label_target': 'Cartella:',
    'placeholder_select_directory': 'Seleziona una cartella da analizzare...',
    'btn_browse': 'Sfoglia...',
    'dialog_file_select': 'Seleziona cartella',
    'label_sensitivity': 'Sensibilità:',
    'combo_strict': 'Rigoroso',
    'combo_balanced': 'Bilanciato',
    'combo_fuzzy': 'Approssimato',
    'tooltip_sensitivity': (
        'Rigoroso = corrispondenza esatta (SHA-256)\n'
        'Bilanciato = quasi esatto, veloce (inizio+fine)\n'
        'Approssimato = contenuto simile (SimHash)'
    ),
    'btn_analyze': 'Analizza',
    'btn_auto_clean': 'Pulizia automatica duplicati',
    'tooltip_auto_clean': (
        'Sposta automaticamente le copie ridondanti in quarantena.\n'
        'Conserva il file con il percorso più breve e pulito.'
    ),
    'btn_open_quarantine': 'Apri cartella quarantena',
    'btn_empty_quarantine': 'Svuota quarantena',
    'tree_folder': 'Cartella',
    'tree_files': 'File',
    'tree_dupes': 'Duplicati',
    'tree_size': 'Dimensione',
    'btn_select_duplicates': 'Seleziona duplicati',
    'tooltip_select_duplicates': 'Seleziona tutte le copie duplicate (gli originali restano deselezionati)',
    'btn_deselect_all': 'Deseleziona tutto',
    'btn_quarantine_selected': 'Quarantena selezionati',
    'btn_delete_selected': 'Elimina selezionati',
    'tree_filename': 'Nome file',
    'tree_verdict': 'Verdetto',
    'label_comparison': 'Confronto',
    'tooltip_waste_donut': 'Rapporto spazio sprecato',
    'tooltip_waste_no_data': 'Nessun dato — avvia prima Analizza',
    'tooltip_waste_detail': 'Spazio sprecato: {waste} / {total} ({pct}%)',
    'menu_help': 'Aiuto',
    'menu_how_it_works': 'Come funziona',
    'menu_about': 'Informazioni',
    'menu_language': 'Lingua',
    'context_open_folder': 'Apri cartella contenitore',
    'status_quarantine_label': 'QUARANTENA',
    'status_quarantined': 'IN QUARANTENA',
    'status_match': 'DUPLICATO ({count})',
    'status_unique': 'Unico',
    'status_match_child': 'Duplicato',
    'comp_file_a': 'FILE A:',
    'comp_file_b': 'FILE B:',
    'comp_size': 'Dimensione:',
    'comp_size_diff': 'Differenza di dimensione:',
    'comp_text_sim': 'Similarità testuale:',
    'comp_simhash_sim': 'Similarità SimHash:',
    'comp_hamming': 'Distanza di Hamming:',
    'comp_binary': '[File binario o protetto]',
    'status_settings_changed': "Impostazioni modificate — riavvia l'analisi.",
    'status_checked': '{count} copie duplicate selezionate.',
    'status_no_dupes_to_check': 'Nessun duplicato da selezionare — scegli prima una cartella.',
    'status_nothing_checked': 'Nessuna selezione.',
    'status_quarantined_files': '{moved}/{total} file messi in quarantena.',
    'status_deleted_files': '{deleted}/{total} file eliminati.',
    'status_no_dupes_found': 'Nessun duplicato trovato — avvia ANALIZZA.',
    'status_no_redundant': 'Nessuna copia ridondante da spostare.',
    'status_no_quarantine': 'Nessuna cartella di quarantena trovata.',
    'status_quarantine_empty': 'La quarantena è già vuota.',
    'status_scan_complete': (
        'Fatto: {total_files} file, {dupe_groups} gruppi di duplicati, '
        '{dupe_files} copie ridondanti — {waste_str} sprecati.'
    ),
    'status_wizard_moved': "L'assistente ha spostato {moved}/{total} file in quarantena.",
    'status_purged': '{deleted}/{total} file eliminati dalla quarantena.',
    'dialog_invalid_path': 'Percorso non valido',
    'dialog_quarantine': 'Quarantena',
    'dialog_delete': 'Eliminazione definitiva',
    'dialog_auto_wizard': 'Assistente intelligente',
    'dialog_purge': 'Svuota quarantena',
    'msg_invalid_path': 'Cartella non trovata:\n{path}',
    'msg_quarantine_confirm': 'Spostare {count} file selezionati in quarantena?',
    'msg_delete_confirm': (
        'ELIMINARE DEFINITIVAMENTE {count} file selezionati?\n'
        'Questa azione è irreversibile.'
    ),
    'msg_wizard_confirm': (
        "L'assistente ha identificato {count} copie ridondanti.\n"
        'Spostarle in quarantena?\n\n'
        '(Conserva il file con il percorso più breve e pulito in ogni gruppo.)'
    ),
    'msg_purge_confirm': (
        'ELIMINARE DEFINITIVAMENTE tutti i {count} file in quarantena?\n'
        'Questa azione è irreversibile.'
    ),
    'help_how_it_works': (
        '<h3>Avvio rapido</h3>'
        '<ol>'
        '<li><b>Imposta una cartella di destinazione</b> — digita un percorso o clicca <i>Sfoglia...</i></li>'
        '<li><b>Scegli la sensibilità:</b><br>'
        '&nbsp;&nbsp;Rigoroso — corrispondenza esatta (SHA-256, zero falsi positivi)<br>'
        '&nbsp;&nbsp;Bilanciato — quasi esatto, veloce (confronta inizio + fine)<br>'
        '&nbsp;&nbsp;Approssimato — trova contenuto simile (~85%+ sovrapposizione)</li>'
        '<li><b>Clicca Analizza</b> — la scansione viene eseguita in background</li>'
        '<li><b>Clicca una cartella</b> a sinistra per vedere i file a destra</li>'
        '<li><b>Clicca un file</b> per confrontarlo con il duplicato nel pannello inferiore</li>'
        '<li><b>Pulisci:</b> seleziona i duplicati, poi metti in quarantena o elimina</li>'
        '</ol>'
        '<h3>Pipeline di rilevamento</h3>'
        '<p><b>Rigoroso e Bilanciato</b> usano una pipeline progressiva:<br>'
        'dimensione file → primi 4 KB → ultimi 4 KB → SHA-256 completo (solo Rigoroso).<br>'
        'Ogni fase elimina i non-candidati prima di leggere altri dati.</p>'
        '<p><b>Approssimato</b> tokenizza il testo (o usa n-grammi di byte per i binari), '
        'calcola un SimHash a 64 bit e lo divide in 8 bande LSH. '
        'I file che condividono una banda vengono segnalati come simili.</p>'
        '<h3>Quarantena</h3>'
        '<p>I file non vengono mai eliminati direttamente — vengono prima spostati in una '
        "cartella <code>_FORENSIC_QUARANTINE</code> all'interno della cartella di destinazione. "
        'Puoi esaminarli, ripristinarli manualmente o usare '
        '<i>Svuota quarantena</i> per eliminarli definitivamente.</p>'
        '<h3>Pulizia automatica</h3>'
        "<p>L'assistente sceglie quale copia conservare usando euristiche: "
        "percorso più breve, assenza di parole chiave come 'copia' o 'backup', "
        'e data di modifica più recente come spareggio. '
        'Tutte le altre copie vengono messe in quarantena.</p>'
        '<h3>Sicurezza e avvertenze</h3>'
        '<p><b>Esegui il backup dei dati prima di usare questo strumento.</b> Sebbene siano '
        'presenti diverse protezioni — finestre di conferma, fase di quarantena prima '
        "dell'eliminazione, e nessun file viene eliminato senza azione esplicita — "
        'nessun software è infallibile.</p>'
        '<p>I file eliminati potrebbero essere recuperabili dal cestino del '
        'sistema operativo a seconda della piattaforma e configurazione.</p>'
        "<p>Questo software è fornito così com'è, senza garanzie di alcun tipo. "
        'Gli autori non sono responsabili per la perdita di dati. '
        "<b>L'uso è interamente a proprio rischio.</b></p>"
    ),
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>Versione 1.0.0</p>'
        '<p>Rilevatore di file duplicati con rilevamento di qualità forense.</p>'
        '<p>Algoritmi: SHA-256, pipeline progressiva inizio/fine, '
        'SimHash + bande LSH.</p>'
        '<p>Costruito con Python e PyQt5.</p>'
        '<hr>'
        '<p><b>Installa:</b> <code>pip install dedupgenie</code><br>'
        '<b>Avvia:</b> <code>dedupgenie</code><br>'
        '<b>PyPI:</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub:</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>Creato da <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'con <b>Gemini</b> e <b>Claude</b>.</p>'
    ),
},

# ======================================================================
# العربية (Arabic)
# ======================================================================
'ar': {
    'window_title': 'DedupGenie',
    'label_target': 'المجلد المستهدف:',
    'placeholder_select_directory': 'اختر مجلداً للفحص...',
    'btn_browse': 'استعراض...',
    'dialog_file_select': 'اختيار مجلد',
    'label_sensitivity': 'الحساسية:',
    'combo_strict': 'صارم',
    'combo_balanced': 'متوازن',
    'combo_fuzzy': 'تقريبي',
    'tooltip_sensitivity': (
        'صارم = تطابق تام (SHA-256)\n'
        'متوازن = شبه تام وسريع (بداية+نهاية)\n'
        'تقريبي = محتوى مشابه (SimHash)'
    ),
    'btn_analyze': 'تحليل',
    'btn_auto_clean': 'تنظيف تلقائي للمكررات',
    'tooltip_auto_clean': (
        'نقل النسخ الزائدة تلقائياً إلى الحجر.\n'
        'يحتفظ بالملف ذي المسار الأقصر والأنظف.'
    ),
    'btn_open_quarantine': 'فتح مجلد الحجر',
    'btn_empty_quarantine': 'إفراغ الحجر',
    'tree_folder': 'مجلد',
    'tree_files': 'ملفات',
    'tree_dupes': 'مكررات',
    'tree_size': 'الحجم',
    'btn_select_duplicates': 'تحديد المكررات',
    'tooltip_select_duplicates': 'تحديد جميع النسخ المكررة (تبقى الأصلية غير محددة)',
    'btn_deselect_all': 'إلغاء تحديد الكل',
    'btn_quarantine_selected': 'حجر المحددة',
    'btn_delete_selected': 'حذف المحددة',
    'tree_filename': 'اسم الملف',
    'tree_verdict': 'النتيجة',
    'label_comparison': 'المقارنة',
    'tooltip_waste_donut': 'نسبة المساحة المهدرة',
    'tooltip_waste_no_data': 'لا توجد بيانات — شغّل التحليل أولاً',
    'tooltip_waste_detail': 'المساحة المهدرة: {waste} / {total} ({pct}%)',
    'menu_help': 'مساعدة',
    'menu_how_it_works': 'كيف يعمل',
    'menu_about': 'حول',
    'menu_language': 'اللغة',
    'context_open_folder': 'فتح المجلد الحاوي',
    'status_quarantine_label': 'حجر',
    'status_quarantined': 'محجور',
    'status_match': 'مكرر ({count})',
    'status_unique': 'فريد',
    'status_match_child': 'مكرر',
    'comp_file_a': 'ملف أ:',
    'comp_file_b': 'ملف ب:',
    'comp_size': 'الحجم:',
    'comp_size_diff': 'فرق الحجم:',
    'comp_text_sim': 'تشابه النص:',
    'comp_simhash_sim': 'تشابه SimHash:',
    'comp_hamming': 'مسافة هامنغ:',
    'comp_binary': '[ملف ثنائي أو محمي]',
    'status_settings_changed': 'تم تغيير الإعدادات — أعد التحليل للتحديث.',
    'status_checked': 'تم تحديد {count} نسخة مكررة.',
    'status_no_dupes_to_check': 'لا توجد مكررات للتحديد — اختر مجلداً أولاً.',
    'status_nothing_checked': 'لا شيء محدد.',
    'status_quarantined_files': 'تم حجر {moved}/{total} ملفات.',
    'status_deleted_files': 'تم حذف {deleted}/{total} ملفات.',
    'status_no_dupes_found': 'لم يتم العثور على مكررات — شغّل التحليل.',
    'status_no_redundant': 'لا توجد نسخ زائدة لنقلها.',
    'status_no_quarantine': 'لم يتم العثور على مجلد حجر.',
    'status_quarantine_empty': 'الحجر فارغ بالفعل.',
    'status_scan_complete': (
        'تم: {total_files} ملف، {dupe_groups} مجموعة مكررة، '
        '{dupe_files} نسخة زائدة — {waste_str} مهدرة.'
    ),
    'status_wizard_moved': 'نقل المساعد {moved}/{total} ملفات إلى الحجر.',
    'status_purged': 'تم حذف {deleted}/{total} ملفات من الحجر.',
    'dialog_invalid_path': 'مسار غير صالح',
    'dialog_quarantine': 'حجر',
    'dialog_delete': 'حذف نهائي',
    'dialog_auto_wizard': 'مساعد التنظيف الذكي',
    'dialog_purge': 'إفراغ الحجر',
    'msg_invalid_path': 'المجلد غير موجود:\n{path}',
    'msg_quarantine_confirm': 'نقل {count} ملف(ات) محددة إلى الحجر؟',
    'msg_delete_confirm': (
        'حذف {count} ملف(ات) محددة نهائياً؟\n'
        'لا يمكن التراجع عن هذا الإجراء.'
    ),
    'msg_wizard_confirm': (
        'حدد المساعد {count} نسخة زائدة.\n'
        'نقلها إلى الحجر؟\n\n'
        '(يحتفظ بالملف ذي المسار الأقصر والأنظف في كل مجموعة.)'
    ),
    'msg_purge_confirm': (
        'حذف جميع الـ {count} ملف(ات) في الحجر نهائياً؟\n'
        'لا يمكن التراجع عن هذا الإجراء.'
    ),
    'help_how_it_works': (
        '<h3>بداية سريعة</h3>'
        '<ol>'
        '<li><b>حدد المجلد المستهدف</b> — اكتب مساراً أو انقر <i>استعراض...</i></li>'
        '<li><b>اختر وضع الحساسية:</b><br>'
        '&nbsp;&nbsp;صارم — تطابق تام (SHA-256، بدون إيجابيات كاذبة)<br>'
        '&nbsp;&nbsp;متوازن — شبه تام وسريع (يقارن البداية + النهاية)<br>'
        '&nbsp;&nbsp;تقريبي — يجد المحتوى المشابه (~85%+ تداخل)</li>'
        '<li><b>انقر تحليل</b> — يعمل الفحص في الخلفية</li>'
        '<li><b>انقر على مجلد</b> في اليمين لرؤية ملفاته في اليسار</li>'
        '<li><b>انقر على ملف</b> لمقارنته مع المكرر في اللوحة السفلية</li>'
        '<li><b>نظّف:</b> حدد المكررات، ثم احجرها أو احذفها</li>'
        '</ol>'
        '<h3>خط أنابيب الكشف</h3>'
        '<p><b>الصارم والمتوازن</b> يستخدمان خط أنابيب تدريجي:<br>'
        'حجم الملف ← أول 4 كيلوبايت ← آخر 4 كيلوبايت ← SHA-256 كامل (الصارم فقط).<br>'
        'كل مرحلة تستبعد غير المرشحين قبل قراءة المزيد من البيانات.</p>'
        '<p><b>التقريبي</b> يحلل النص (أو يستخدم n-grams للملفات الثنائية)، '
        'يحسب SimHash بـ 64 بت ويقسمه إلى 8 نطاقات LSH. '
        'الملفات التي تتشارك نطاقاً تُعلّم كمتشابهة.</p>'
        '<h3>الحجر</h3>'
        '<p>لا تُحذف الملفات مباشرة أبداً — تُنقل أولاً إلى مجلد '
        '<code>_FORENSIC_QUARANTINE</code> داخل المجلد المستهدف. '
        'يمكنك مراجعتها، استعادتها يدوياً، أو استخدام '
        '<i>إفراغ الحجر</i> لحذفها نهائياً.</p>'
        '<h3>التنظيف التلقائي</h3>'
        '<p>يختار المساعد النسخة المراد الاحتفاظ بها باستخدام معايير: '
        "أقصر مسار، غياب كلمات مثل 'نسخة' أو 'احتياطي'، "
        'وأحدث تاريخ تعديل كفاصل. '
        'جميع النسخ الأخرى تُنقل إلى الحجر.</p>'
        '<h3>السلامة وإخلاء المسؤولية</h3>'
        '<p><b>انسخ بياناتك احتياطياً قبل استخدام هذه الأداة.</b> رغم وجود عدة '
        'إجراءات حماية — مربعات تأكيد، مرحلة حجر قبل الحذف، '
        'ولا يُحذف أي ملف بدون إجراء صريح — '
        'لا يوجد برنامج معصوم من الخطأ.</p>'
        '<p>قد تكون الملفات المحذوفة قابلة للاسترداد من سلة المحذوفات '
        'حسب نظام التشغيل والإعدادات.</p>'
        '<p>يُقدم هذا البرنامج كما هو، بدون أي ضمانات. '
        'المؤلفون غير مسؤولين عن أي فقدان للبيانات. '
        '<b>استخدامك لهذه الأداة على مسؤوليتك الكاملة.</b></p>'
    ),
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>الإصدار 1.0.0</p>'
        '<p>كاشف الملفات المكررة بجودة جنائية.</p>'
        '<p>الخوارزميات: SHA-256، خط أنابيب تدريجي للبداية/النهاية، '
        'SimHash + نطاقات LSH.</p>'
        '<p>مبني بـ Python و PyQt5.</p>'
        '<hr>'
        '<p><b>التثبيت:</b> <code>pip install dedupgenie</code><br>'
        '<b>التشغيل:</b> <code>dedupgenie</code><br>'
        '<b>PyPI:</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub:</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>أنشأه <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'بمساعدة <b>Gemini</b> و <b>Claude</b>.</p>'
    ),
},

# ======================================================================
# Português
# ======================================================================
'pt': {
    'window_title': 'DedupGenie',
    'label_target': 'Destino:',
    'placeholder_select_directory': 'Selecione uma pasta para analisar...',
    'btn_browse': 'Procurar...',
    'dialog_file_select': 'Selecionar pasta',
    'label_sensitivity': 'Sensibilidade:',
    'combo_strict': 'Rigoroso',
    'combo_balanced': 'Equilibrado',
    'combo_fuzzy': 'Aproximado',
    'tooltip_sensitivity': (
        'Rigoroso = correspondência exata (SHA-256)\n'
        'Equilibrado = quase exato, rápido (início+fim)\n'
        'Aproximado = conteúdo semelhante (SimHash)'
    ),
    'btn_analyze': 'Analisar',
    'btn_auto_clean': 'Limpeza automática de duplicados',
    'tooltip_auto_clean': (
        'Move cópias redundantes automaticamente para quarentena.\n'
        'Mantém o arquivo com o caminho mais curto e limpo.'
    ),
    'btn_open_quarantine': 'Abrir pasta de quarentena',
    'btn_empty_quarantine': 'Esvaziar quarentena',
    'tree_folder': 'Pasta',
    'tree_files': 'Arquivos',
    'tree_dupes': 'Duplicados',
    'tree_size': 'Tamanho',
    'btn_select_duplicates': 'Selecionar duplicados',
    'tooltip_select_duplicates': 'Selecionar todas as cópias duplicadas (originais ficam desmarcados)',
    'btn_deselect_all': 'Desmarcar tudo',
    'btn_quarantine_selected': 'Quarentena selecionados',
    'btn_delete_selected': 'Excluir selecionados',
    'tree_filename': 'Nome do arquivo',
    'tree_verdict': 'Veredicto',
    'label_comparison': 'Comparação',
    'tooltip_waste_donut': 'Proporção de espaço desperdiçado',
    'tooltip_waste_no_data': 'Sem dados — execute Analisar primeiro',
    'tooltip_waste_detail': 'Espaço desperdiçado: {waste} / {total} ({pct}%)',
    'menu_help': 'Ajuda',
    'menu_how_it_works': 'Como funciona',
    'menu_about': 'Sobre',
    'menu_language': 'Idioma',
    'context_open_folder': 'Abrir pasta contêiner',
    'status_quarantine_label': 'QUARENTENA',
    'status_quarantined': 'EM QUARENTENA',
    'status_match': 'DUPLICADO ({count})',
    'status_unique': 'Único',
    'status_match_child': 'Duplicado',
    'comp_file_a': 'ARQUIVO A:',
    'comp_file_b': 'ARQUIVO B:',
    'comp_size': 'Tamanho:',
    'comp_size_diff': 'Diferença de tamanho:',
    'comp_text_sim': 'Similaridade textual:',
    'comp_simhash_sim': 'Similaridade SimHash:',
    'comp_hamming': 'Distância de Hamming:',
    'comp_binary': '[Arquivo binário ou protegido]',
    'status_settings_changed': 'Configurações alteradas — analise novamente.',
    'status_checked': '{count} cópias duplicadas marcadas.',
    'status_no_dupes_to_check': 'Nenhum duplicado para marcar — selecione uma pasta primeiro.',
    'status_nothing_checked': 'Nada marcado.',
    'status_quarantined_files': '{moved}/{total} arquivos em quarentena.',
    'status_deleted_files': '{deleted}/{total} arquivos excluídos.',
    'status_no_dupes_found': 'Nenhum duplicado encontrado — execute ANALISAR.',
    'status_no_redundant': 'Nenhuma cópia redundante para mover.',
    'status_no_quarantine': 'Nenhuma pasta de quarentena encontrada.',
    'status_quarantine_empty': 'A quarentena já está vazia.',
    'status_scan_complete': (
        'Concluído: {total_files} arquivos, {dupe_groups} grupos de duplicados, '
        '{dupe_files} cópias redundantes — {waste_str} desperdiçados.'
    ),
    'status_wizard_moved': 'O assistente moveu {moved}/{total} arquivos para quarentena.',
    'status_purged': '{deleted}/{total} arquivos removidos da quarentena.',
    'dialog_invalid_path': 'Caminho inválido',
    'dialog_quarantine': 'Quarentena',
    'dialog_delete': 'Exclusão permanente',
    'dialog_auto_wizard': 'Assistente inteligente',
    'dialog_purge': 'Esvaziar quarentena',
    'msg_invalid_path': 'Pasta não encontrada:\n{path}',
    'msg_quarantine_confirm': 'Mover {count} arquivo(s) marcados para quarentena?',
    'msg_delete_confirm': (
        'EXCLUIR PERMANENTEMENTE {count} arquivo(s) marcados?\n'
        'Esta ação não pode ser desfeita.'
    ),
    'msg_wizard_confirm': (
        'O assistente identificou {count} cópias redundantes.\n'
        'Mover para quarentena?\n\n'
        '(Mantém o arquivo com o caminho mais curto e limpo em cada grupo.)'
    ),
    'msg_purge_confirm': (
        'EXCLUIR PERMANENTEMENTE todos os {count} arquivo(s) na quarentena?\n'
        'Esta ação não pode ser desfeita.'
    ),
    'help_how_it_works': (
        '<h3>Início rápido</h3>'
        '<ol>'
        '<li><b>Defina a pasta alvo</b> — digite um caminho ou clique em <i>Procurar...</i></li>'
        '<li><b>Escolha a sensibilidade:</b><br>'
        '&nbsp;&nbsp;Rigoroso — correspondência exata (SHA-256, zero falsos positivos)<br>'
        '&nbsp;&nbsp;Equilibrado — quase exato, rápido (compara início + fim)<br>'
        '&nbsp;&nbsp;Aproximado — encontra conteúdo semelhante (~85%+ sobreposição)</li>'
        '<li><b>Clique em Analisar</b> — a análise é executada em segundo plano</li>'
        '<li><b>Clique numa pasta</b> à esquerda para ver seus arquivos à direita</li>'
        '<li><b>Clique num arquivo</b> para compará-lo com o duplicado no painel inferior</li>'
        '<li><b>Limpe:</b> selecione os duplicados, depois coloque em quarentena ou exclua</li>'
        '</ol>'
        '<h3>Pipeline de detecção</h3>'
        '<p><b>Rigoroso e Equilibrado</b> usam um pipeline progressivo:<br>'
        'tamanho do arquivo → primeiros 4 KB → últimos 4 KB → SHA-256 completo (apenas Rigoroso).<br>'
        'Cada etapa elimina não-candidatos antes de ler mais dados.</p>'
        '<p><b>Aproximado</b> tokeniza o texto (ou usa n-gramas de bytes para binários), '
        'calcula um SimHash de 64 bits e divide-o em 8 bandas LSH. '
        'Arquivos que compartilham uma banda são sinalizados como semelhantes.</p>'
        '<h3>Quarentena</h3>'
        '<p>Os arquivos nunca são excluídos diretamente — são primeiro movidos para uma '
        'pasta <code>_FORENSIC_QUARANTINE</code> dentro da pasta alvo. '
        'Você pode revisá-los, restaurá-los manualmente ou usar '
        '<i>Esvaziar quarentena</i> para excluí-los permanentemente.</p>'
        '<h3>Limpeza automática</h3>'
        '<p>O assistente escolhe qual cópia manter usando heurísticas: '
        "caminho mais curto, ausência de palavras-chave como 'cópia' ou 'backup', "
        'e data de modificação mais recente como desempate. '
        'Todas as outras cópias são movidas para quarentena.</p>'
        '<h3>Segurança e aviso legal</h3>'
        '<p><b>Faça backup dos seus dados antes de usar esta ferramenta.</b> Embora várias '
        'proteções estejam em vigor — diálogos de confirmação, etapa de quarentena antes '
        'da exclusão, e nenhum arquivo é excluído sem ação explícita — '
        'nenhum software é infalível.</p>'
        '<p>Arquivos excluídos podem ser recuperáveis da lixeira do '
        'sistema operacional dependendo da plataforma e configuração.</p>'
        '<p>Este software é fornecido como está, sem garantias de qualquer tipo. '
        'Os autores não são responsáveis por perda de dados. '
        '<b>O uso é inteiramente por sua conta e risco.</b></p>'
    ),
    'help_about': (
        '<h3>DedupGenie</h3>'
        '<p>Versão 1.0.0</p>'
        '<p>Detector de arquivos duplicados com detecção de qualidade forense.</p>'
        '<p>Algoritmos: SHA-256, pipeline progressivo início/fim, '
        'SimHash + bandas LSH.</p>'
        '<p>Construído com Python e PyQt5.</p>'
        '<hr>'
        '<p><b>Instalar:</b> <code>pip install dedupgenie</code><br>'
        '<b>Executar:</b> <code>dedupgenie</code><br>'
        '<b>PyPI:</b> <a href="https://pypi.org/project/dedupgenie/">pypi.org/project/dedupgenie</a><br>'
        '<b>GitHub:</b> <a href="https://github.com/lemarcgagnon/DuplicateFinder">github.com/lemarcgagnon/DuplicateFinder</a></p>'
        '<hr>'
        '<p>Criado por <b>Marc Gagnon</b> '
        '(<a href="https://marcgagnon.ca">marcgagnon.ca</a>)<br>'
        'com <b>Gemini</b> e <b>Claude</b>.</p>'
    ),
},

}  # end _STRINGS


def get_translator(lang='en'):
    """Return a translator function for the given language code.

    Usage:
        tr = get_translator('fr')
        tr('btn_analyze')                        # → 'Analyser'
        tr('status_match', count=3)              # → 'DOUBLON (3)'
        tr('nonexistent_key')                    # → falls back to English
    """
    strings = _STRINGS.get(lang, _STRINGS['en'])
    fallback = _STRINGS['en']

    def tr(key, **kwargs):
        text = strings.get(key) or fallback.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    return tr
