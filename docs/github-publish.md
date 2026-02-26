# GitHub Publish Checklist

Wenn du lokal Commits siehst, aber nichts auf GitHub erscheint, fehlt meistens der Remote oder der Push.

## 1) Remote prüfen

```bash
git remote -v
```

Wenn keine Ausgabe kommt, ist kein GitHub-Remote konfiguriert.

## 2) Remote setzen

```bash
git remote add origin <GITHUB_REPO_URL>
```

Beispiel:

```bash
git remote add origin git@github.com:dein-org/compliance-hub.git
```

## 3) Branch pushen

```bash
git push -u origin work
```

## 4) Pull Request öffnen

Nach dem Push den PR gegen `main` in GitHub öffnen.

## Hinweis

In dieser Umgebung wurden Commits lokal erstellt. Ohne konfigurierten Remote kann nichts auf GitHub sichtbar werden.
