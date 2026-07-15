
## Simulador de Garra Mecánica 2D: Motor de Transformaciones Lineales

Este proyecto es un simulador interactivo de una garra mecánica (máquina atrapa-peluches) desarrollado íntegramente en Python. A diferencia de aplicaciones convencionales que delegan la física y el movimiento a motores gráficos preconstruidos, este simulador está **estrictamente gobernado por el Álgebra Lineal**. 

Toda posición, rotación, escalado, jerarquía de objetos y sistema de colisión es el resultado directo de cálculos explícitos con matrices homogéneas de 3x3. Las imágenes en pantalla son meros representativos pasivos de la data matemática subyacente.

---

## 🧠 Filosofía y Decisiones de Diseño Arquitectónico

El principio fundamental del proyecto es: **"La matemática es la fuente de la verdad"**. 
Para lograr esto, el sistema se desacopló en 5 capas, garantizando que la lógica algebraica nunca se mezcle con las librerías de dibujo.

### 1. El Motor Matemático (Capa 1)
La base de todo el sistema reside en `math_engine.py`, construido sobre **NumPy**. Se decidió utilizar coordenadas homogéneas (matrices de $3 \times 3$ para un entorno 2D) por una razón matemática crítica: **permitir que la traslación sea tratada como una multiplicación de matrices** en lugar de una simple suma de vectores. Esto permite componer múltiples transformaciones en un solo paso.

Las decisiones de diseño matemático incluyen:
* **Composición Estricta ($M = T \cdot R \cdot S$):** Cualquier estado local de un objeto se calcula multiplicando secuencialmente su matriz de Traslación ($T$), Rotación ($R$) y Escala ($S$). El orden de multiplicación no es conmutativo y se aplica de derecha a izquierda sobre los vértices locales.
* **Manejo de Inversas ($M^{-1}$):** Para las demostraciones de telemetría, el motor es capaz de calcular la matriz inversa. La multiplicación de $M \cdot M^{-1}$ devuelve la Matriz Identidad ($I$), garantizando que el sistema es algebraicamente reversible y no sufre de degradación de datos (Gimbal lock o pérdida de precisión extrema).

### 2. Scene Graph y Jerarquía Matricial (Capa 2)
Implementado en `scene_graph.py`. Los objetos en la simulación no tienen posiciones absolutas flotando en el vacío; pertenecen a un **Grafo de Escena**.
* La garra ("Brazo") es hija del Mundo.
* Las pinzas ("PinzaIzq", "PinzaDer") son hijas del Brazo.
* **Propagación de Transformaciones:** La posición real de la punta de una pinza en la pantalla se calcula mediante la multiplicación de las matrices de sus ancestros:
  $$M_{global\_pinza} = M_{global\_mundo} \cdot M_{local\_brazo} \cdot M_{local\_pinza}$$
* **Re-emparentamiento Dinámico (Captura):** Cuando la garra atrapa una caja, la caja deja de ser hija del "Mundo" y pasa a ser hija del "Brazo". Su matriz local se recalcula instantáneamente para que conserve su posición visual exacta, absorbiendo matemáticamente la escala y traslación de su nuevo padre.

### 3. Colisiones Numéricas vs. Gráficas (Capa 4)
No se utilizan *Bounding Boxes* (cajas de colisión de píxeles) tradicionales. El agarre de las cajas se define puramente por vectores:
1. **Distancia Euclidiana:** Se calcula el vector global de las puntas de las pinzas y el vector global del anclaje de la caja. Si $\vert{} \vec{p}_{pinzas} - \vec{p}_{caja} \vert{} < \text{Tolerancia}$, están lo suficientemente cerca en los ejes X e Y.
2. **Validación de Escala (Profundidad):** En nuestro entorno 2D simulamos el eje Z escalando los objetos. La garra no puede atrapar una caja si no están en el mismo "plano de profundidad". Se compara la norma euclidiana de la primera columna de sus matrices globales ($\vert{}\vert{} M_{0,0}, M_{1,0} \vert{}\vert{}$) para autorizar el agarre.

### 4. Telemetría y Transparencia (Capa 5)
Para demostrar la solidez del motor, se desarrolló un panel lateral interactivo (`math_panel.py`) que audita en tiempo real al sistema. Descompone analíticamente la Matriz Global del nodo seleccionado y extrae usando funciones trigonométricas e iteraciones exactas la posición, el ángulo y el factor de escala, culminando con una demostración visual de la Matriz Identidad.

---

## 📂 Estructura del Proyecto

```text
/simulador_garra
├── assets/
│   ├── brazo.png, pinza_izq.png, pinza_der.png, caja.png
│   └── fondo.png
├── main.py             # Bucle de juego, eventos y Máquina de Estados
├── math_engine.py      # Motor de Álgebra Lineal puro (NumPy)
├── scene_graph.py      # Nodos jerárquicos y cálculo de M_global
├── renderer.py         # Abstracción de dibujo (Pygame)
├── math_panel.py       # UI de telemetría y descomposición analítica
└── README.md           # Documentación técnica

```

## 🚀 Instalación y Ejecución

### Prerrequisitos

El proyecto requiere Python 3.10 o superior.

### Dependencias

Instala las librerías necesarias ejecutando:

Bash

```
pip install numpy pygame

```

### Ejecutar el simulador

Inicia el programa desde la terminal:

Bash

```
python main.py

```

## 🎮 Controles y Funcionalidades

El simulador implementa una máquina de estados finitos que bloquea o habilita acciones dependiendo de la situación matemática actual (Ej. No puedes abrir las pinzas mientras retornas al origen).

**Tecla / Acción**

**Descripción**

**Lógica Subyacente**

**← / →**

Traslación del Brazo (Eje X)

Suma/resta constante en la matriz $T_{local}$ del brazo.

**↑ / ↓**

Escalado / Profundidad (Eje Z)

Modifica uniformemente la matriz $S_{local}$ del brazo.

**Espacio**

Abrir / Cerrar Pinzas

Aplica un factor de Rotación ($\pm 28^\circ$) en la matriz $R_{local}$ de las pinzas. Valida el _re-parenting_ de cajas.

**R**

Retorno a Home (Drop)

Activa LERP lineal de velocidad constante en $T$ y $S$ hasta alcanzar el vector origen, soltando el objeto (des-emparentado) al finalizar.

**TAB / Clic Izq**

Clicar Objetos

Recorre el árbol del Grafo de Escena para auditar matemáticamente el objeto en el panel derecho.

**D**

Modo Debug

Alterna la visualización gráfica de los ejes de coordenadas locales de cada matriz.

## 🧪 Pruebas de Verificación Matemática

Al utilizar este software como demostrador técnico, recomendamos prestar atención al **Panel de Análisis Matricial** (HUD Derecho).

Se insta a observar cómo, al seleccionar una pinza en movimiento, los coeficientes de las componentes trigonométricas de la matriz de rotación fluctúan conservando siempre la estructura ortogonal, probando que el _Math Engine_ es dimensionalmente estable.


