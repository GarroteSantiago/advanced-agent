# Guion de preparacion para la presentacion final

Este documento es para que cualquier integrante pueda presentar el proyecto sin
tener que leer todo el repositorio. La idea es entender el relato, saber que
demuestra cada slide y poder responder preguntas tecnicas del examen.

## Resumen en 60 segundos

`advanced-agent` es un harness de agente de codigo escrito en Python. No usa
LangChain, LangGraph ni frameworks de orquestacion: el loop, la delegacion, las
herramientas, la memoria, RAG, las politicas y la observabilidad estan
implementados como componentes propios.

El caso de uso elegido es analizar un repositorio FastAPI desconocido y generar
un informe verificable: arquitectura, rutas, dependencias, comandos utiles,
riesgos y evidencia. El agente principal coordina subagentes especializados y,
al final, un `Scribe` escribe los resultados en una carpeta de documentacion.

Lo importante para defender no es solo que "usa IA". Lo importante es que el
agente esta construido como software inspeccionable: tiene objetos con
responsabilidades claras, tests, limites de seguridad, trazas y evidencia real
de ejecucion.

## Como contar la historia

La presentacion sigue este orden:

1. Que construimos.
2. Que problema concreto resuelve.
3. Como esta organizado internamente.
4. Como funciona el loop de razonamiento.
5. Como colaboran los objetos en runtime.
6. Como se divide el trabajo entre subagentes.
7. Como usa RAG y memoria persistente.
8. Como controla efectos laterales y genera trazas.
9. Que evidencia real hay.
10. Cual es la conclusion tecnica.

La frase central: **construimos un agente avanzado como una pieza de
infraestructura mantenible, no como un prompt grande pegado a herramientas.**

## Guion por diapositiva

### 1. Advanced Agent

Mensaje: este proyecto es un agente de codigo inspeccionable.

Que decir:
- "Es un harness propio en Python para ejecutar un agente de codigo."
- "Tiene delegacion multiagente, RAG, memoria persistente, politicas y
  observabilidad."
- "La decision clave fue no usar LangChain ni LangGraph, para que cada mecanismo
  sea visible y testeable."

Prueba en el repo:
- `README.md`
- `src/harness/`
- `src/agent/`
- `src/tests/`

### 2. Caso de uso

Mensaje: el agente analiza un repo FastAPI desconocido y produce un informe
verificable.

Que decir:
- "Elegimos este caso porque se puede corregir objetivamente."
- "Si el informe dice cual es el entry point, como se conectan las rutas o que
  comando corre los tests, eso se puede comprobar en archivos reales."
- "No es una tarea estetica; es una tarea verificable."

Prueba en el repo:
- `docs/use-case.md`
- `scripts/sample_app/`
- `docs/evidence/task-evidence.md`

### 3. Arquitectura

Mensaje: la arquitectura usa capas tipo onion.

Que decir:
- "En el centro estan los conceptos puros: loop, runtime, tools, eventos,
  ledger."
- "Hacia afuera estan los adaptadores: OpenAI, web search, filesystem,
  observabilidad, JSON memory."
- "Los puertos apuntan hacia adentro. Eso permite testear con fakes y cambiar
  proveedores sin cambiar el core."

Terminos que deben sonar:
- `ChatModel`
- `EmbeddingModel`
- `ToolInterface`
- `Approver`
- `MemoryStore`

Prueba en el repo:
- `docs/architecture.md`
- `docs/diagrams/ownership.svg`
- `src/llm/ports/`
- `src/harness/tools/`

### 4. Loop de ejecucion

Mensaje: el loop es pequeno y las transiciones son explicitas.

Que decir:
- "`AgentLoop` no decide inteligencia. Solo ejecuta una fase y pregunta al
  `Navigator` que sigue."
- "Las fases son el ciclo ReAct: `Reason`, `Act`, `Observe`."
- "El `Navigator` devuelve `Continue(next phase)` o `Halt`; no hay `None`
  ambiguo."

Prueba en el repo:
- `src/harness/loop/agent_loop.py`
- `src/harness/loop/navigator.py`
- `src/harness/loop/phases/`

### 5. Un turno

Mensaje: durante un turno se puede seguir cada llamada entre objetos.

Que decir:
- "La conversacion entra por `Session`."
- "`AgentLoop` corre fases."
- "`ReasonPhase` llama al modelo."
- "`ActionPhase` pasa por `ToolExecutor`."
- "`ObservationPhase` actualiza contexto y consulta controles."
- "Todo publica eventos en `EventBus`."

Prueba en el repo:
- `docs/diagrams/runtime-collaboration.svg`
- `docs/diagrams/sequence.svg`
- `src/harness/events/`

### 6. Equipo de subagentes

Mensaje: el agente principal coordina roles con herramientas y permisos
diferentes.

Que decir:
- "`Explorer` mira estructura y archivos."
- "`Researcher` usa RAG y web."
- "`Implementer` propone cambios, pero no escribe."
- "`Tester` puede ejecutar comandos."
- "`Reviewer` valida la respuesta."
- "`Scribe` es el unico escritor y solo escribe documentacion."

Punto importante:
- El `Scribe` no depende de que el modelo se acuerde de llamarlo bien. Se invoca
  al final con el ledger completo mediante `Documenter`.

Prueba en el repo:
- `src/agent/team.py`
- `src/agent/subagent.py`
- `src/agent/documenter.py`

### 7. RAG y memoria persistente

Mensaje: el agente no depende solo de memoria del modelo.

Que decir:
- "El `Researcher` consulta primero `rag_search` sobre una base FastAPI."
- "El corpus se chunkifica, se embebe y se guarda en un `NumpyVectorStore`."
- "Cada resultado recuperado se registra como `Source(Origin.RAG)`."
- "La memoria persistente guarda aprendizajes del proyecto entre ejecuciones."

Numeros a recordar:
- Aproximadamente 275 chunks del corpus FastAPI.
- En la segunda ejecucion se recordaron 7 entradas de memoria.

Prueba en el repo:
- `docs/rag-base.md`
- `src/rag/`
- `src/agent/rag_tool.py`
- `src/memory/`
- `docs/evidence/task-2-memory-recall.txt`

### 8. Seguridad y observabilidad

Mensaje: las acciones con efecto lateral estan controladas y trazadas.

Que decir:
- "`ToolExecutor` es el unico punto por donde pasan herramientas."
- "Antes de ejecutar, consulta un `Approver`."
- "`PolicyVerifier` aplica reglas de lectura, escritura, comandos y workspace."
- "`EventBus` emite eventos de modelo, tools, retrieval, guards y resultado."
- "La ejecucion real genero 59 spans de OpenTelemetry."

Prueba en el repo:
- `src/harness/tools/executor.py`
- `src/harness/tools/policy.py`
- `src/observability/`
- `docs/evidence/repo-analysis.otel.jsonl`

### 9. Evidencia

Mensaje: hay ejecuciones reales, no solo una arquitectura dibujada.

Que decir:
- "Run 1 hizo 47 model calls."
- "Consulto 44 fuentes RAG."
- "El `Scribe` escribio 3 documentos de agentes."
- "Run 2 demostro memoria persistente porque recordo entradas anteriores."

Prueba en el repo:
- `docs/evidence/task-1-analysis.txt`
- `docs/evidence/task-2-memory-recall.txt`
- `docs/evidence/analysis/sample_app/explore.md`
- `docs/evidence/analysis/sample_app/research.md`
- `docs/evidence/analysis/sample_app/test.md`

### 10. Conclusion

Mensaje: el valor del proyecto es que el agente esta construido como
infraestructura mantenible.

Que decir:
- "No es solo un prompt largo."
- "Tiene seams explicitos: loop, tools, memory, RAG, events."
- "Tiene autonomia limitada: roles, policies, iteration caps."
- "Tiene evidencia honesta: docs, tests, trazas y limitaciones."

Cerrar con:
- "La idea principal es que un agente avanzado puede ser verificable,
  observable y seguro si se disena como software."

## Conceptos clave para estudiar

### `AgentLoop`

Es el driver del agente. Ejecuta fases y delega la decision de la siguiente fase
al `Navigator`.

### `Navigator`

Contiene la tabla de transiciones. Devuelve `Continue(next phase)` o `Halt`.

### `AgentExecutionContext`

Contexto inmutable que viaja por las fases. Cada cambio devuelve una nueva
version.

### `TaskLedger`

Estado compartido de la tarea. Guarda request original, resultados de
subagentes, fuentes, archivos modificados y observaciones.

### `Subagent`

Agente especializado con prompt, tools, permisos e iteration cap propios.

### `DelegatingActionPhase`

Fase que convierte una llamada del agente principal a un subagente en una
ejecucion real y luego mezcla el reporte en el `TaskLedger`.

### `RAG`

Retrieval-Augmented Generation. En este proyecto se usa para consultar
documentacion FastAPI antes de responder sobre convenciones del framework.

### `ProjectMemory`

Memoria persistente por proyecto. Se carga al inicio de una ejecucion y se
actualiza al final.

### `ToolExecutor`

Punto unico de ejecucion de herramientas. Antes de invocar una tool consulta el
`Approver`.

### `PolicyVerifier`

Valida reglas de seguridad: rutas prohibidas, comandos prohibidos, aprobaciones
requeridas y confinamiento de workspace.

### `EventBus`

Canal de eventos del sistema. Permite progreso en CLI, auditoria y trazas
OpenTelemetry/Phoenix.

### `Scribe`

Subagente que escribe documentacion. Es el unico con `write_file` y esta
confinado al directorio de docs.

## Preguntas probables del examen

### Por que no usar LangChain o LangGraph?

Porque el requisito valoraba construir sobre el agente de clase y entender los
mecanismos internos. Al no usar frameworks de orquestacion, el loop, la
delegacion, las tools, la memoria y la observabilidad quedan visibles,
testeables y explicables.

### Como se diferencia este proyecto de un chatbot con tools?

Tiene un harness completo: fases ReAct, estado compartido, politicas por tool,
subagentes con permisos distintos, RAG con provenance, memoria persistente y
observabilidad.

### Como funciona la delegacion?

El principal no hace todo. Puede llamar subagentes como si fueran tools. La
`DelegatingActionPhase` ejecuta el `Subagent`, recibe un `SubagentReport` y lo
mezcla en el `TaskLedger`.

### Como se evita que un subagente haga algo peligroso?

Cada tool call pasa por `ToolExecutor`, que consulta `Approver` y
`PolicyVerifier`. Ademas cada subagente tiene un set limitado de tools. Por
ejemplo, `Scribe` puede escribir, pero solo dentro de docs.

### Para que sirve RAG aqui?

Sirve para que el `Researcher` confirme convenciones FastAPI con documentos
recuperados, no solo con conocimiento del modelo. Las fuentes recuperadas se
registran como `Origin.RAG`.

### Como funciona la memoria persistente?

`ProjectMemoryService` carga memoria al inicio de la ejecucion y absorbe
resultados del `TaskLedger` al final. La memoria se guarda por proyecto en JSON.

### Que captura la observabilidad?

Eventos de llamadas al modelo, tools, documentos recuperados, errores, guards,
tokens, latencia, costo estimado y resultado final. Puede exportarse como spans
OpenTelemetry.

### Cuales son las limitaciones honestas?

- El manejo de contexto es estructural, no un resumen semantico.
- La memoria persistente existe, pero la categorizacion todavia es gruesa.
- Las fuentes RAG estan bien etiquetadas, pero repo/web no se auto-etiquetan al
  mismo nivel.
- Modelos pequenos pueden llegar al iteration cap; en ese caso se devuelven
  hallazgos parciales.

## Ruta de demo sugerida

Abrir en este orden:

1. `docs/presentation.html`
2. `docs/diagrams/ownership.svg`
3. `src/harness/loop/agent_loop.py`
4. `src/agent/team.py`
5. `src/harness/runtime/ledger.py`
6. `docs/evidence/task-evidence.md`
7. `docs/evidence/analysis/sample_app/research.md`
8. `docs/evidence/repo-analysis.otel.jsonl`

Si hay poco tiempo, mostrar solo:

1. La presentacion.
2. `src/agent/team.py` para probar los subagentes.
3. `src/harness/loop/agent_loop.py` para probar el loop.
4. `docs/evidence/task-evidence.md` para probar que hubo ejecuciones reales.

## Reparto sugerido para el equipo

Persona 1:
- Slides 1-2.
- Explica objetivo, restricciones y caso de uso.

Persona 2:
- Slides 3-5.
- Explica arquitectura, loop y runtime collaboration.

Persona 3:
- Slides 6-8.
- Explica subagentes, RAG, memoria, seguridad y observabilidad.

Persona 4:
- Slides 9-10.
- Explica evidencia, limitaciones y cierre.

## Checklist antes de presentar

- Abrir `docs/presentation.html` en el navegador.
- Probar flechas izquierda/derecha.
- Tener listos los archivos de evidencia.
- Saber explicar `AgentLoop`, `TaskLedger`, `ToolExecutor`, `RAG` y `Scribe`.
- Recordar los numeros: 196 tests, 275 chunks, 59 spans, 47 model calls, 44
  fuentes RAG, 7 entradas de memoria recordadas.
- No venderlo como perfecto: mencionar las limitaciones de `docs/reflection.md`.
