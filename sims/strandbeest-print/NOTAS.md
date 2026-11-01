# Notas de diseño: lo aprendido

Lo que vale para cualquier pieza nueva de esta carpeta. Las medidas marcadas como *pendiente* esperan a la
probeta (`probeta.py`). Cuando haya resultados de impresión, se anotan aquí con fecha.

## Impresoras y material
- Bambu Lab A1 (con AMS/BMCU) y P2S Combo (AMS). Cama 256 × 256. PLA, boquilla 0,4.
- Los proyectos `.3mf` se generan para la P2S y la A1 (0.4) con `bbl/make_configs.py`, que construye la configuración a
  partir de los perfiles oficiales de Bambu (herencias, includes, variante de boquilla "Direct Drive Standard").
- PLA es frágil en ajustes a presión (lección del Strandbeest paramétrico de nablu): si la probeta falla, PETG en las piezas con tetones o clics.

## Holguras (verificadas en simulación, *pendiente* de confirmar impresas)
| Uso | Valor |
|---|---|
| Piezas que giran o deslizan (mínimo aceptado en barridos) | ≥ 0,19 mm; normal 0,23–0,35 |
| Print-in-place | 0,35 |
| Engranajes m1: backlash | 0,5 (0,75 en los primeros diseños) |
| Pivote: agujero sobre tornillo M3 / pasador Ø3 | Ø3,5 |
| Tetón a presión Ø2,5 (aplanado en la cara de la cama) en agujero ciego | Ø2,4 (*pendiente*: probeta v2 A, 2,3 / 2,4 / 2,5) |
| Tapón sobre rosca M3 | agujero Ø2,7 (*pendiente*: probeta B, 2,6 / 2,7 / 2,8) |
| Cierre a presión de tapas | labio a 0,15 de la pared, cordón r 0,45 → 0,3 de apriete en ranura r 0,6 (**confirmado**) |
| Eje en D Ø6, plano a 2,2: agujero en D | +0,2 en radio y en plano (**confirmado**) ; cojinete horizontal Ø6,6 (*pendiente* v2 D) |
| Lengüetas en ranuras (deslizar) | +0,25 |
| Encaje de capas de color impresas aparte (descartado) | 0,08 |

## Resultados de impresión
### 2026-11-01 · probeta v1 (P2S, PLA)
- **A, tetones horizontales:** salen con rebaba debajo (la cara inferior del cilindro cuelga 0,25 mm sobre la cama) y no
  entran. → v2: tetón desplazado 0,45 hacia la cama y cortado plano allí (se imprime apoyado), punta achaflanada 0,3.
  Regla: **ningún cilindro horizontal a menos de ~0,5 mm de la cama sin aplanarlo.**
- **B:** sin probar (falta tornillo M3).
- **C, cordón del cierre:** entra bien en la ranura. OK.
- **D:** arandela en D entra bien y arrastra con el eje (OK). Cojinete Ø6,7 impreso con el agujero vertical: holgado.
  → los cojinetes reales tienen el agujero horizontal (salen algo más justos); diseño a Ø6,6 y la probeta v2 los prueba
  de pie, 6,4 / 6,6 / 6,8.
- **E:** el piñón entra perfecto en el eje del TT (OK). La placa de prueba no se pudo probar: su pie chocaba con el cuerpo
  del motor (fallo de la probeta, no del soporte real, que se ha comprobado sin choque). → v2: placa más larga, pie debajo del motor.

## Motor TT (LA001, kit Marble Run 003)
- 59 rpm a 5 V. Eje en D: Ø5,4, planos a 3,7 → agujero en el piñón Ø5,6 con planos a 3,95.
- Para fijarlo en una placa: saliente del eje (agujero Ø9), tetón a +11,15 mm del eje (agujero Ø4,1),
  bulto a +30,7 (ranura 5,6 × 4,6). Envolvente de la caja reductora: 18,8 × 22,4 × 48,4 (de −11,2 a +37,2 desde el eje).
- No basta con colocarlo: hay que apretarlo contra la placa (en el cuadro vivo, nervios en la pared de la caja, 0,05 de apriete).
- Piñón en el eje D (Ø5,6, planos 3,95): **confirmado**. Saliente, tetón y bulto: *pendiente* (probeta v2 E).

## Uniones sin pegamento (lo que se ha elegido y por qué)
- **Colores con AMS:** cada color es una columna que sale de la base hasta su altura, y los colores superiores atraviesan
  a los inferiores. Nada flota, nada se pega. Una lámina de color impresa aparte encima de otra solo funciona pegada.
- **Brazo en una pieza plana:** dos tetones Ø2,5 en agujeros ciegos (la lámina se imprime cara atrás en la cama, así que
  los brazos que salen hacia atrás se imprimen aparte).
- **Pivotes:** tornillo M3 avellanado (DIN 7991) por detrás, al ras; un pasador impreso de Ø3 y 24 mm de alto es demasiado frágil.
- **Caja:** un tubo de una pieza impreso de pie (sin soportes); tapas delante y detrás con labio y cordón a presión;
  paneles interiores con lengüetas en ranuras abiertas por detrás y cerradas por delante (tope); soportes en raíles del suelo.
- **Ejes:** cabeza en un extremo, engranaje en D en el otro; las excéntricas quedan atrapadas por su horquilla
  (pestaña a un lado, arandela en D al otro, 1 mm de juego porque la horquilla se inclina con su lámina).

## Errores que ya han pasado (comprobar siempre)
- **Piezas que no están unidas:** comprobar `len(m.decompose()) == 1` en toda pieza que deba ser una. Pasó con el engranaje
  doble (hueco de 0,6 entre ruedas) y con la lámina de la ola (las patas no tocaban la ola).
- **Pinzamientos de malla:** regiones 2D que se tocan en un punto dan mallas no estancas. Limpiar con
  `buffer(-0.1).buffer(0.1)` y descartar trozos < 0,6 mm².
- **Pasadores con tope fijo:** si el tope va impreso en la punta, la pieza no se puede meter. El tope va aparte.
- **Láminas de color "flotando":** en un apilado, una capa alta sin nada debajo no se puede imprimir ni pegar en su sitio.
- **Tetones tangentes:** dos cilindros que se tocan en una línea dan aristas no-manifold.

## 3MF para Bambu Studio
- 3MF genérico (núcleo + `m:colorgroup`, `pid`/`pindex` por objeto): Bambu solo carga geometría y color, sin placas
  ("El 3mf no es de Bambu Lab…"). Una pieza multicolor = objeto con `components`, un componente por color.
- Proyecto de Bambu (placas y filamentos ya puestos): `Application` = `BambuStudio-…`, objetos en `3D/Objects/*.model`
  referenciados con `p:path`, `Metadata/model_settings.config` (partes con `extruder`, placas con `model_instance`)
  y un `Metadata/project_settings.config` completo (se parte de uno guardado por Bambu: `bbl/project_settings_A1_8xPLA.json`).
- **Los id de los sub-objetos deben ser únicos entre todos los archivos** `3D/Objects/*.model`: Bambu los empareja solo por id
  (con id repetidos, todas las piezas cargaron la forma de la primera).
- Placas: columnas = `ceil(sqrt(n))`, paso 256 × 1,2 = 307,2 mm; la placa i empieza en (col · 307,2, −fila · 307,2).

## Herramientas externas usadas
- **bambox** (estampo/bambox): idea de generar `project_settings.config` desde perfil de máquina + filamentos. Solo trae
  la P1S, así que `bbl/make_configs.py` hace lo mismo desde los perfiles oficiales de BambuStudio.
- **cq_gears** (meadiode/cq_gears): referencia de evolvente. `check_gears.py` confirma que nuestros dientes son la evolvente
  menos 0,25 mm (la mitad del backlash) y que los pares engranan con ≥ 0,2 mm en un barrido fino.
- **bd_warehouse**: medidas de la cabeza del M3 avellanado (ISO 10642, Ø5,64) → avellanado de 90° con +0,2.
- **Bambu Studio en línea de comandos**: no se pudo instalar aquí (las descargas de releases de GitHub están bloqueadas en
  este entorno). En su lugar, `bbl/check_3mf.py` repite las comprobaciones del cargador de Bambu.
- No usados: CamFollowerJS (nuestras levas son excéntricas circulares) y wk_mechanics (Blender, de pago).

## Verificación que se hace siempre
- Barrido del ciclo completo (cada 10–15°) con `min_gap` entre todos los pares que se mueven.
- Lo oculto no asoma por la ventana en ninguna posición.
- Todas las mallas estancas al volver a leer el 3MF.
- Vista previa de las placas en imagen antes de entregar.
- `bbl/check_3mf.py` sobre cada proyecto: placas, id únicos, piezas dentro de su placa, mallas estancas.
- `check_gears.py` si cambian los engranajes.
- Para dientes, barrido 2D fino (cientos de pasos por diente): el barrido 3D del ciclo no basta.
