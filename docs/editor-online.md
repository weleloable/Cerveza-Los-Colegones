# Editor de recetas online (Streamlit Community Cloud)

Contraseña del editor: **colegones**

El editor (`pages/1_Editor.py`) se publica en Streamlit Cloud. Con un token de GitHub en
los secretos, cada guardado es un commit de `Recetas_Cerveza.json` en `main`. La PWA
(GitHub Pages) muestra el cambio 1-2 minutos después, cuando Pages termina de construir.
Sin token, el editor sigue editando el archivo local como siempre.

## 1. Crear el token de GitHub (una vez)

1. GitHub > tu foto > Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
2. Repository access: **Only select repositories** > `Cerveza-Los-Colegones`.
3. Permissions > Repository permissions > **Contents: Read and write**. Nada más.
4. Caducidad: la que quieras. Cuando caduque el editor dirá "No pude cargar las recetas de GitHub: 401"; se genera otro y se cambia en el paso 3.
5. Copia el token (empieza por `github_pat_`). Solo se muestra una vez.

## 2. Publicar la app

1. Entra en https://share.streamlit.io con tu cuenta de GitHub.
2. Create app > Deploy a public app from GitHub.
3. Repository `weleloable/Cerveza-Los-Colegones`, branch `main`, main file path `pages/1_Editor.py`.
4. Elige un subdominio (por ejemplo `colegones-editor`).

## 3. Poner el token (Advanced settings > Secrets)

```toml
GITHUB_TOKEN = "github_pat_xxxxxxxx"
```

Opcionales, con estos valores por defecto: `GITHUB_REPO = "weleloable/Cerveza-Los-Colegones"`, `GITHUB_RAMA = "main"`.

Deploy. Al abrirlo, la barra lateral debe decir "Guardando en GitHub". Si dice "archivo local", el token no llegó.

## Cosas a saber

- Dos personas a la vez: si una guarda mientras la otra tiene el editor abierto, la segunda ve
  "Otra persona guardó antes que tú", pulsa "Recargar desde Archivo" y repite su cambio. Nadie pisa a nadie.
- La app se duerme tras un rato sin uso y tarda unos 30 segundos en despertar.
- No subas nunca el token al repo. `.streamlit/secrets.toml` está en `.gitignore`.

## Probar en local con el token

```
mkdir .streamlit
# crea .streamlit/secrets.toml con la línea GITHUB_TOKEN = "..."
python -m streamlit run pages/1_Editor.py
```

Tests: `python -m unittest discover -s tests -t .`
