 % SIMULACIÓN NÚMERICA MOTOR RAMJET

% Constantes
R = 287; % Constante de gas para el aire en J/(kg*K)
gamma = 1.4; % Coeficiente adiabático para el aire
Cp = gamma * R / (gamma - 1); % Calor específico a presión constante

% Condiciones iniciales
rho_0 = 1.225; % Densidad del aire en kg/m^3
P_0 = 101325; % Presión inicial en Pa
T_0 = 288.15; % Temperatura inicial en K
M_0 = 2.0; % Número de Mach inicial (supersónico)

% Flujo másico inicial
A_1 = 0.1; % Área de entrada en m^2
U_1 = M_0 * sqrt(gamma * R * T_0); % Velocidad inicial en m/s
m_dot = rho_0 * U_1 * A_1; % Flujo másico constante en kg/s

% Balance de energía para la combustión
LHV = 43e6; % Poder calorífico inferior del combustible en J/kg
f = 0.02; % Relación de combustible/aire
Q_in = f * m_dot * LHV;

% Longitud de las secciones
L_comp = 0.4; % Longitud de compresión en metros
L_comb = 0.4; % Longitud de combustión en metros (transición gradual)
L_exp = 1.0; % Longitud de expansión en metros

% Perfil de área no lineal
function dA_dx = area_variation(x, L)
    if x < L/2
        dA_dx = -0.1 * sin(pi * x / L); % Contracción (compresión)
    else
        dA_dx = 0.1 * sin(pi * (x - L/2) / L); % Expansión
    end
end

% Dinámica de Mach y temperatura para compresión y expansión
function dY_dx = ramjet_dynamics(x, Y, gamma, R, L)
    M = Y(1);
    T = Y(2);
    A = Y(3);
    
    dA_dx = area_variation(x, L);
    dM = dM_dx(M, gamma, A, dA_dx);
    dT = -((gamma - 1) * T * dM) / (1 + (gamma - 1) / 2 * M^2);
    dY_dx = [dM; dT; dA_dx];
end

% Dinámica de la combustión con transición suave
function dY_dx = ramjet_dynamics_combustion(x, Y, gamma, R, Q_in, m_dot, Cp, L_comb)
    M = Y(1);
    T = Y(2);
    A = Y(3);
    
    % Cambio gradual de temperatura en la combustión
    dT = (Q_in / (m_dot * Cp)) * (1 / L_comb); % Incremento de T distribuido a lo largo de L_comb
    dM = 0; % Suponemos que el Mach no cambia significativamente
    dA_dx = 0; % Área constante en la cámara de combustión
    
    dY_dx = [dM; dT; dA_dx];
end

% Función para dM/dx
function dM = dM_dx(M, gamma, A, dA_dx)
    dM = (2 / (M * (1 + (gamma - 1) / 2 * M^2))) * (dA_dx / A) * (M^2 - 1);
end

% Intervalo de integración para cada sección
x_span_comp = [0, L_comp];
x_span_comb = [L_comp, L_comp + L_comb];
x_span_exp = [L_comp + L_comb, L_comp + L_comb + L_exp];

% Valores iniciales para la compresión
Y_init_comp = [M_0; T_0; A_1];

% Integrar la compresión
[x_comp, Y_comp] = ode45(@(x, Y) ramjet_dynamics(x, Y, gamma, R, L_comp), x_span_comp, Y_init_comp);

% Valores iniciales para la combustión (al final de la compresión)
Y_init_comb = [Y_comp(end, 1); Y_comp(end, 2); Y_comp(end, 3)];

% Integrar la combustión con transición suave
[x_comb, Y_comb] = ode45(@(x, Y) ramjet_dynamics_combustion(x, Y, gamma, R, Q_in, m_dot, Cp, L_comb), x_span_comb, Y_init_comb);

% Valores iniciales para la expansión (al final de la combustión)
Y_init_exp = [Y_comb(end, 1); Y_comb(end, 2); Y_comb(end, 3)];

% Integrar la expansión
[x_exp, Y_exp] = ode45(@(x, Y) ramjet_dynamics(x, Y, gamma, R, L_exp), x_span_exp, Y_init_exp);

% Extraer resultados
x_total = [x_comp; x_comb; x_exp];
M_total = [Y_comp(:, 1); Y_comb(:, 1); Y_exp(:, 1)];
T_total = [Y_comp(:, 2); Y_comb(:, 2); Y_exp(:, 2)];
A_total = [Y_comp(:, 3); Y_comb(:, 3); Y_exp(:, 3)];
U_total = M_total .* sqrt(gamma * R .* T_total);

% Cálculo de densidad y presión
rho_total = m_dot ./ (U_total .* A_total); % Densidad en función de flujo másico y velocidad
P_total = rho_total .* R .* T_total; % Presión en función de densidad y temperatura

% Gráficas con delimitación de secciones
figure;
plot(x_total, M_total, 'k');
xlabel('Posición (x)');
ylabel('Número de Mach (M)');
title('Variación del Número de Mach en el Motor RAMJET');
hold on;
xline(L_comp, '--', 'Compresión');
xline(L_comp + L_comb, '--', 'Combustión');
xline(L_comp + L_comb + L_exp, '--', 'Expansión');
hold off;

figure;
plot(x_total, T_total, 'g');
xlabel('Posición (x)');
ylabel('Temperatura (T) en K');
title('Variación de la Temperatura en el Motor RAMJET');
hold on;
xline(L_comp, '--', 'Compresión');
xline(L_comp + L_comb, '--', 'Combustión');
xline(L_comp + L_comb + L_exp, '--', 'Expansión');
hold off;

figure;
plot(x_total, P_total, 'r');
xlabel('Posición (x)');
ylabel('Presión (P) en Pa');
title('Variación de la Presión en el Motor RAMJET');
hold on;
xline(L_comp, '--', 'Compresión');
xline(L_comp + L_comb, '--', 'Combustión');
xline(L_comp + L_comb + L_exp, '--', 'Expansión');
hold off;

figure;
plot(x_total, A_total, 'm');
xlabel('Posición (x)');
ylabel('Área (A) en m^2');
title('Variación del Área en el Motor RAMJET');
hold on;
xline(L_comp, '--', 'Compresión');
xline(L_comp + L_comb, '--', 'Combustión');
xline(L_comp + L_comb + L_exp, '--', 'Expansión');
hold off;

figure;
plot(x_total, U_total, 'b');
xlabel('Posición (x)');
ylabel('Velocidad (u) en m/s');
title('Variación de la Velocidad u(x) en el Motor RAMJET');
hold on;
xline(L_comp, '--', 'Compresión');
xline(L_comp + L_comb, '--', 'Combustión');
xline(L_comp + L_comb + L_exp, '--', 'Expansión');
hold off;