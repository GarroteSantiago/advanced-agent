# Guion de presentacion final

Este guion acompana `docs/presentation.html`. Esta actualizado para la version
con evidencia real en Phoenix: una captura del arbol de trazas y otra de los
atributos de un span LLM.

## Relato central

Construimos un agente de codigo inspeccionable en Python. No usamos LangChain ni
LangGraph: el loop, la delegacion, las tools, la memoria, RAG, las politicas y
la observabilidad estan implementados como componentes propios.

El caso de uso es concreto y verificable: analizar un repositorio FastAPI
desconocido (`scripts/sample_app`) y producir un informe con arquitectura,
rutas, dependencias, riesgos, comandos y evidencia.

La tesis de la presentacion:

> Un agente avanzado no deberia ser solo un prompt grande con tools. Puede ser
> infraestructura mantenible: con boundaries claros, estado auditable, permisos,
> memoria, RAG, tests y trazas persistidas.

## Resumen de 60 segundos

`advanced-agent` ejecuta una tarea de analisis de repositorio mediante un agente
principal y subagentes especializados. El principal coordina, los subagentes
exploran, investigan, prueban o documentan, y todo se acumula en un
`TaskLedger`.

La ejecucion queda documentada de tres maneras:

- Evidencia textual: `docs/evidence/task-1-analysis.txt` y
  `docs/evidence/task-2-memory-recall.txt`.
- Documentacion escrita por el `Scribe`: `docs/evidence/analysis/sample_app/`.
- Observabilidad: Phoenix muestra un root span `agent.run`, spans `llm` y
  `tool`, costos, latencia, tokens y atribucion por agente.

## Guion por slide

### 1. Title - Agente de codigo inspeccionable

Mensaje: este proyecto es un agente de codigo construido como software, no como
una demo opaca.

Decir:

- "Este es un harness propio en Python para un agente de codigo."
- "Tiene multiagente, RAG, memoria persistente, politicas de seguridad y
  observabilidad."
- "La restriccion importante fue no delegar la orquestacion en un framework:
  queriamos poder explicar y testear cada mecanismo."

Pruebas:

- `README.md`
- `src/harness/`
- `src/agent/`
- `src/tests/`

### 2. Use Case - Analisis verificable de repositorios FastAPI

Mensaje: elegimos un caso que se puede corregir objetivamente.

Decir:

- "El input es `scripts/sample_app`, un proyecto FastAPI pequeno."
- "El output esperado no es subjetivo: entry point, routers, endpoints,
  dependencias, comandos y riesgos se verifican contra archivos reales."
- "Por eso sirve para demostrar un agente auditable."

Pruebas:

- `docs/use-case.md`
- `scripts/sample_app/`
- `docs/evidence/task-evidence.md`

### 3. Architecture - Capas tipo onion

Mensaje: el core no depende de proveedores externos.

Decir:

- "En el centro estan el loop, runtime, ledger, events, tools y policies."
- "En el borde estan OpenAI, Tavily, filesystem, memoria JSON, RAG y Phoenix."
- "Los puertos apuntan hacia adentro, asi podemos usar fakes en tests y cambiar
  adaptadores sin reescribir el core."

Terminos clave:

- `ChatModel`
- `EmbeddingModel`
- `ToolInterface`
- `Approver`
- `MemoryStore`

Pruebas:

- `docs/architecture.md`
- `docs/diagrams/ownership.svg`
- `src/llm/ports/`
- `src/harness/tools/`

### 4. Loop - Ciclo explicito de ejecucion

Mensaje: el loop es pequeno y las transiciones son controladas.

Decir:

- "`AgentLoop` ejecuta fases, pero no mezcla todas las responsabilidades."
- "Las fases siguen un ReAct simple: reason, act, observe."
- "`Navigator` decide la siguiente fase con una tabla explicita: continue o
  halt."
- "Esto hace que el comportamiento sea testeable y no dependa de convenciones
  invisibles."

Pruebas:

- `src/harness/loop/agent_loop.py`
- `src/harness/loop/navigator.py`
- `src/harness/loop/phases/`

### 5. Collaboration - Un turno en runtime

Mensaje: cada llamada importante entre objetos se puede seguir.

Decir:

- "`Session` recibe la tarea."
- "`AgentLoop` corre las fases."
- "`ReasonPhase` llama al modelo."
- "`ActionPhase` pasa por `ToolExecutor`."
- "`ObservationPhase` actualiza contexto y controles."
- "Todo publica eventos en `EventBus`, que alimenta CLI, auditoria y trazas."

Pruebas:

- `docs/diagrams/runtime-collaboration.svg`
- `src/harness/events/`
- `src/harness/runtime/`

### 6. Agent Roles - Principal y subagentes

Mensaje: la delegacion tiene roles, permisos y estado compartido.

Decir:

- "El principal coordina y sintetiza."
- "`Explorer` lee estructura y archivos."
- "`Researcher` usa RAG y web fallback."
- "`Tester` puede ejecutar comandos."
- "`Reviewer` valida gaps."
- "`Scribe` es el unico escritor y esta confinado a docs."
- "Los subagentes devuelven `SubagentReport`; el resultado se mezcla en el
  `TaskLedger`."

Pruebas:

- `src/agent/team.py`
- `src/agent/subagent.py`
- `src/agent/documenter.py`
- `src/harness/runtime/ledger.py`

### 7. RAG Documentation - Fuentes y embeddings

Mensaje: el agente no responde solo desde conocimiento del modelo.

Decir:

- "El `Researcher` consulta primero `rag_search` sobre documentacion FastAPI."
- "El corpus se divide en chunks, se embebe y se guarda localmente."
- "Cada recuperacion se registra como fuente RAG en el ledger."
- "Esto permite decir de donde salio la informacion."

Numeros:

- Aproximadamente 275 chunks de documentacion FastAPI.
- Embeddings con `text-embedding-3-small`.

Pruebas:

- `docs/rag-base.md`
- `src/rag/`
- `src/agent/rag_tool.py`

### 8. Storage - Persistencia simple y local

Mensaje: elegimos almacenamiento simple porque el corpus y la demo son acotados.

Decir:

- "El indice RAG usa `NumpyVectorStore`: embeddings en `.npy` y chunks en
  JSON."
- "La memoria persistente usa `JsonMemoryStore`, una memoria por proyecto."
- "La evidencia vive en archivos versionables: transcripts, docs del Scribe y
  trazas."
- "No necesitamos una base vectorial externa para este tamano; menos
  dependencias hace mas reproducible la demo."

Pruebas:

- `src/rag/store.py`
- `src/memory/store.py`
- `data/rag_index/`

### 9. Safety Observability - Efectos laterales y eventos

Mensaje: las acciones estan controladas y todo queda narrado como eventos.

Decir:

- "`ToolExecutor` es el unico punto de ejecucion de herramientas."
- "Antes de ejecutar, consulta `Approver` y `PolicyVerifier`."
- "Las reglas cubren lectura, escritura, comandos y confinement del workspace."
- "`EventBus` emite llamadas de modelo, tools, retrieval, guards y resultado."
- "Esos eventos son la base de la auditoria y de los spans OpenTelemetry."

Pruebas:

- `src/harness/tools/executor.py`
- `src/harness/tools/policy.py`
- `src/harness/events/`
- `src/observability/`

### 10. Execution Run 1 - Primera corrida

Mensaje: no es una arquitectura dibujada; hay ejecucion real.

Decir:

- "Run 1 analiza `scripts/sample_app` desde cero."
- "Produce un informe sobre entry point, routers, endpoints, dependencias,
  riesgos y comandos."
- "Consulta fuentes RAG y delega a subagentes."
- "El Scribe escribe documentos por agente."

Pruebas:

- `docs/evidence/task-1-analysis.txt`
- `docs/evidence/analysis/sample_app/explore.md`
- `docs/evidence/analysis/sample_app/research.md`
- `docs/evidence/analysis/sample_app/test.md`

### 11. Execution Run 2 - Memoria persistente

Mensaje: la segunda corrida prueba que hay memoria entre procesos.

Decir:

- "Run 2 vuelve a analizar el proyecto, pero arranca con memoria previa."
- "La memoria no es contexto del chat; se carga desde storage al inicio y se
  absorbe al final."
- "Esto demuestra persistencia por proyecto."

Pruebas:

- `docs/evidence/task-2-memory-recall.txt`
- `src/memory/`
- `data/memory/`

### 12. Observability Trace - Phoenix persistente

Mensaje: la trazabilidad ahora se ve en Phoenix y se puede conservar reiniciando
el servidor con el mismo working dir.

Decir:

- "Antes teniamos un archivo JSONL headless. Ahora tambien guardamos la corrida
  en Phoenix con un servidor persistente."
- "El servidor Phoenix se levanta con `PHOENIX_WORKING_DIR=.phoenix`; si muere,
  se reinicia con el mismo directorio y la traza sigue disponible."
- "La captura izquierda muestra el arbol: `agent.run` como root, spans `llm
  gpt-5-nano` y spans `tool` para explore, list_files, read_file, rag_search."
- "La captura derecha abre un span LLM y muestra tokens, latencia, costo, modelo
  y `agent.name`."
- "Eso prueba trazabilidad end-to-end y observabilidad por operacion."

Comandos usados para el enfoque nuevo:

```sh
PHOENIX_WORKING_DIR=.phoenix \
PHOENIX_PORT=6007 \
PHOENIX_GRPC_PORT=4318 \
uv run phoenix serve
```

```sh
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6007 \
OBSERVABILITY=phoenix \
uv run python scripts/analyze_repo.py
```

Pruebas:

- `docs/evidence/phoenix-trace-tree.png`
- `docs/evidence/phoenix-llm-attributes.png`
- `src/observability/phoenix.py`

### 13. Reflection - Cierre

Mensaje: el valor esta en la ingenieria del agente.

Decir:

- "Lo que funciono: loop propio, ledger immutable, policies, RAG y trazas
  testeables."
- "Lo no perfecto: modelos chicos pueden subdelegar de mas o llegar al
  iteration cap."
- "Mejoras: summarizer semantico, mejor auto-etiquetado de fuentes repo/web,
  digest de memoria y un AwaitInput mas rico."
- "La leccion: la coordinacion confiable debe estar en codigo, no en pedirle al
  modelo que recuerde hacer todo bien."

Pruebas:

- `docs/reflection.md`
- `src/tests/`

## Preguntas probables

### Por que no usar LangChain o LangGraph?

Porque queriamos que el loop, la delegacion, las tools, la memoria y las trazas
fueran visibles, explicables y testeables. El objetivo era construir el agente
como infraestructura propia.

### Como se diferencia de un chatbot con tools?

Tiene fases explicitas, ledger compartido, subagentes con permisos distintos,
RAG con provenance, memoria persistente, policies y observabilidad por eventos.

### Como funciona la delegacion?

El principal llama subagentes como tools. `DelegatingActionPhase` ejecuta el
subagente, recibe un `SubagentReport` y lo integra al `TaskLedger`.

### Como se evita que un subagente haga algo peligroso?

Cada llamada pasa por `ToolExecutor`, que consulta `Approver` y
`PolicyVerifier`. Ademas, cada subagente solo recibe las tools que necesita. El
`Scribe` puede escribir, pero solo en docs.

### Para que sirve RAG aqui?

Para que el `Researcher` confirme convenciones FastAPI con documentacion
recuperada. Las fuentes quedan registradas como `Origin.RAG`.

### Como funciona la memoria persistente?

`ProjectMemoryService` carga memoria al iniciar una ejecucion y absorbe
resultados del ledger al final. El storage actual es JSON por proyecto.

### Que captura Phoenix?

El root span `agent.run`, spans de cada llamada al modelo, spans de cada tool,
tokens, latencia, costo, output, estado y `agent.name`. En la presentacion se
ve una captura del arbol y otra de los atributos LLM.

### Por que ahora Phoenix y no solo JSONL?

El JSONL sigue siendo util como artifact headless, pero Phoenix permite navegar
la traza, abrir spans y mostrar los atributos visualmente. El enfoque nuevo usa
`PHOENIX_WORKING_DIR=.phoenix` para que la data sobreviva a reinicios del
servidor.

### Cuales son las limitaciones honestas?

- El manejo de contexto es estructural, no un resumen semantico profundo.
- La memoria persiste, pero su categorizacion es simple.
- Repo/web sources no estan auto-etiquetadas con el mismo detalle que RAG.
- Con modelos pequenos pueden aparecer partial findings por iteration cap.

## Ruta de demo sugerida

Abrir en este orden:

1. `docs/presentation.html`
2. `src/harness/loop/agent_loop.py`
3. `src/agent/team.py`
4. `src/harness/runtime/ledger.py`
5. `src/observability/phoenix.py`
6. `docs/evidence/phoenix-trace-tree.png`
7. `docs/evidence/phoenix-llm-attributes.png`
8. `docs/evidence/task-evidence.md`

Si hay poco tiempo:

1. La presentacion.
2. `src/agent/team.py` para probar subagentes.
3. `src/harness/loop/agent_loop.py` para probar el loop.
4. La slide de Phoenix para probar trazabilidad real.

## Checklist antes de presentar

- Abrir `docs/presentation.html`.
- Probar flechas izquierda/derecha.
- Probar zoom en las dos capturas Phoenix.
- Tener listas las capturas:
  - `docs/evidence/phoenix-trace-tree.png`
  - `docs/evidence/phoenix-llm-attributes.png`
- Recordar los numeros de la corrida Phoenix mostrada:
  - Latencia aproximada: 2m 21s.
  - Costo total aproximado: USD 0.01.
  - Span LLM mostrado: 16,869 tokens.
- Saber explicar `AgentLoop`, `TaskLedger`, `ToolExecutor`, `RAG`, `Scribe` y
  `PhoenixTracer`.
- No venderlo como perfecto: mencionar las limitaciones de `docs/reflection.md`.
