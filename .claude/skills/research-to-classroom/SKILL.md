---
name: research-to-classroom
description: >
  Convierte investigaciones recientes (tesis, artículos, proyectos de grado de
  estudiantes del curso de Máquinas Térmicas) en módulos pedagógicos dentro de los
  notebooks AVA. Usar SIEMPRE que el usuario mencione incorporar investigación,
  tesis de estudiantes, artículos científicos, nuevos desarrollos, ciclos avanzados
  (sCO2, ORC, cogeneración, hidrógeno, captura de carbono) o transferencia de
  conocimiento científico al aula.
---

# Research-to-Classroom — Transferencia de investigación al AVA

## Objetivo
Cada trabajo de investigación estudiantil se transforma en un "módulo de frontera":
un notebook (o sección) autocontenido que conecta la teoría del sílabo con el avance
científico, manteniendo rigor y trazabilidad de la fuente.

## Estructura obligatoria de un módulo de frontera
1. **Contexto** (≤5 frases): qué limitación del ciclo clásico motiva el avance.
2. **Fundamento**: ecuaciones nuevas o modificadas respecto al modelo del sílabo, en display math, con derivación mínima.
3. **Modelo computacional**: implementación en Python reproducible (CoolProp / REFPROP-backend si aplica; para sCO2 usar `CoolProp` con `CO2` y cuidado cerca del punto crítico).
4. **Widget comparativo**: slider(s) que permitan comparar ciclo clásico vs. avanzado (p.ej. Rankine vs. ORC con distintos fluidos de trabajo en un mismo diagrama T-s).
5. **Resultados de la investigación original**: reproducir al menos una figura o tabla clave del trabajo estudiantil con el código del módulo; reportar la desviación.
6. **Ejercicio de extensión** para el estudiante actual.
7. **Créditos y cita**: nombre del autor estudiantil, año, semestre, DOI/repositorio institucional Javeriana, en formato BibTeX embebido en una celda raw.

## Flujo de trabajo
1. Recibir la fuente (PDF de tesis/artículo). Extraer: pregunta de investigación, modelo matemático, supuestos, datos de validación.
2. Mapear al sílabo: ¿a qué semana/tema del curso se ancla el módulo? Confirmar con el profesor.
3. Verificar reproducibilidad: si el trabajo usó software propietario (Aspen, EES), reimplementar el modelo mínimo en Python y validar contra los resultados publicados (tolerancia documentada).
4. Redactar el módulo siguiendo las reglas de `ava-notebook-enhancer` (texto reducido, ecuaciones densas, widgets).
5. Registrar el módulo en `docs/modules_registry.bib` y en la tabla de trazabilidad `docs/traceability.md` (fuente → módulo → semana del curso → resultados de validación).

## Rigor y ética académica
- Nunca inventar datos de la investigación fuente; si falta un parámetro, marcarlo como supuesto explícito.
- Distinguir tipográficamente lo que es del sílabo estándar vs. contribución del estudiante investigador (usar admonition/callout).
- Toda validación numérica se reporta con % de error frente a la fuente.

## Salida para el artículo de docencia
Cada módulo genera automáticamente una entrada en `docs/case_study_log.md` con: fecha, fuente, esfuerzo de adaptación, decisiones pedagógicas, y métricas (nº de widgets, nº de ecuaciones, líneas de prosa antes/después). Esta bitácora alimenta la skill `teaching-case-docs`.
