# redpolasapps.fyi

Web de Redpolas Apps (GitHub Pages). Las páginas se generan desde `_src/` (GitHub Pages no publica carpetas que empiezan por `_`):

```
python3 _src/build.py
```

- `_src/home.html` → `/` (español) y `/en/` (inglés)
- `_src/linetycoon.html` → `/LineTycoon/` y `/LineTycoon/en/`
- `_src/apps.json` → fichas de apps de la portada, datos estructurados y `sitemap.xml`

Cada fuente se escribe una vez con los dos idiomas: lo que lleva `lang="es"` solo sale en la versión española y lo que lleva `lang="en"`, en la inglesa.

## Añadir una app

1. Icono de 256×256 en `assets/icons/<slug>.png`.
2. Su entrada en `_src/apps.json` (`status`: `live` o `soon`; `appStoreId`; `privacy`; textos `es`/`en`).
3. Su política de privacidad en `/<Carpeta>/privacy.html`.
4. `python3 _src/build.py`, commit y push.

Las políticas de privacidad (`*/privacy.html`) y `app-ads.txt` no se generan: se editan a mano. No cambies sus rutas: están enlazadas desde App Store Connect.
