function [A, re_plot, ri, x, dAdx, st, re_flow, xlip] = ramjet_geometry(p)
% RAMJET_GEOMETRY — Geometria axisimetrica del RAMJET
%
% CLAVES para dA/dx suave SIN oscilaciones:
% 1) Spike termina en ri=0 con m=0 en x3_end = x3 - 7%*l3
%    Entre x3_end y x3 hay zona plana (ri=0, dri=0) => dA/dx continua
% 2) SIN correccion de gap posterior => dredx puro Hermite
% 3) Parametros disenados para gap >= gmin sin forzar nada

arguments
    p struct
end

%% Estaciones
l1=p.l1; l2=p.l2; l3=p.l3; l4=p.l4; l5=p.l5; l6=p.l6;
x0=0; x1=l1; x2=l1+l2; x3=x2+l3;
x4=x3+l4; x5=x4+l5; x6=x5+l6;
st = struct('x0',x0,'x1',x1,'x2',x2,'x3',x3,'x4',x4,'x5',x5,'x6',x6);

x    = linspace(x0, x6, p.N)';
xlip = x1 + p.xlip_frac * l2;
xm   = x2 + p.xm_frac   * l3;
x3e  = x3 - 0.07*l3;   % spike llega a 0 aqui (cola plana hasta x3)

%% Spike ri(x) — Hermite puro, sin correccion
ri    = zeros(size(x));
dridx = zeros(size(x));

idx = (x>=x1) & (x<=xm);
[ri(idx), dridx(idx)] = hd(x(idx), x1,p.ri_x1,0, xm,p.ri_peak,0);

idx = (x>xm) & (x<=x3e);
[ri(idx), dridx(idx)] = hd(x(idx), xm,p.ri_peak,0, x3e,0,0);
% x3e..x6: ri=0, dridx=0 (ya init en cero)

%% Coraza re_flow(x) — Hermite puro, sin correccion
re_flow = zeros(size(x));
dredx   = zeros(size(x));

% Gap del labio: ri en xlip
if xlip <= xm
    ri_xlip = hv(xlip, x1,p.ri_x1,0, xm,p.ri_peak,0);
elseif xlip <= x3e
    ri_xlip = hv(xlip, xm,p.ri_peak,0, x3e,0,0);
else
    ri_xlip = 0;
end
r_lip0 = min(ri_xlip + p.g_lip, 0.87*p.r_inlet);
m_lip  = (p.r_inlet - r_lip0)/(x2 - xlip);

% Labio xlip->x2
idx = (x>=xlip) & (x<=x2);
[re_flow(idx), dredx(idx)] = hd(x(idx), xlip,r_lip0,m_lip, x2,p.r_inlet,m_lip);

% Difusor interno x2->x3  (C1: pendiente m_lip en x2, pendiente 0 en x3)
idx = (x>x2) & (x<=x3);
[re_flow(idx), dredx(idx)] = hd(x(idx), x2,p.r_inlet,m_lip, x3,p.rc,0);

% Camara x3->x4
idx = (x>x3) & (x<=x4);
re_flow(idx) = p.rc; dredx(idx) = 0;

% Convergente x4->x5
idx = (x>x4) & (x<=x5);
[re_flow(idx), dredx(idx)] = hd(x(idx), x4,p.rc,0, x5,p.rcd,0);

% Divergente x5->x6
idx = (x>x5) & (x<=x6);
[re_flow(idx), dredx(idx)] = hd(x(idx), x5,p.rcd,0, x6,p.re_exit,0);

%% Area y dA/dx — 100% analitica
A    = pi*(re_flow.^2 - ri.^2);
A    = max(A,0);
A(x<x2) = NaN;

dAdx = 2*pi*(re_flow.*dredx - ri.*dridx);
dAdx(x<x2) = NaN;

re_plot = re_flow;
re_plot(x<xlip) = NaN;

%% Verificacion gap
idx_d   = (x>=x2)&(x<=x3);
gap_min = min(re_flow(idx_d)-ri(idx_d));
if gap_min < p.gmin
    warning('Gap min=%.1fmm < gmin=%.0fmm. Reduce ri_peak.', gap_min*1e3, p.gmin*1e3);
end

A_fn = @(xq) interp1(x(~isnan(A)),A(~isnan(A)),xq,'pchip');
fprintf('\n=== GEOMETRIA ===\n');
fprintf('  Diametro max coraza : %5.1f mm\n', max(re_flow)*2e3);
fprintf('  Diametro spike max  : %5.1f mm\n', p.ri_peak*2e3);
fprintf('  Diametro garganta   : %5.1f mm\n', p.rcd*2e3);
fprintf('  Diametro salida     : %5.1f mm\n', p.re_exit*2e3);
fprintf('  Gap en x2           : %5.1f mm\n', (interp1(x,re_flow,x2,'pchip')-interp1(x,ri,x2,'pchip'))*1e3);
fprintf('  Gap minimo en ducto : %5.1f mm\n', gap_min*1e3);
fprintf('  A(x2)=%.5f  A(x3)=%.5f  A(x5)=%.5f  A(x6)=%.5f m2\n', A_fn(x2),A_fn(x3),A_fn(x5),A_fn(x6));
fprintf('  dAdx max = %.5f m2/m\n', max(abs(dAdx(~isnan(dAdx)))));
end

function y = hv(x,x0,y0,m0,x1,y1,m1)
    L=x1-x0; t=(x-x0)./L;
    y=(2*t.^3-3*t.^2+1)*y0+(t.^3-2*t.^2+t)*L*m0+(-2*t.^3+3*t.^2)*y1+(t.^3-t.^2)*L*m1;
end

function [y,dy] = hd(x,x0,y0,m0,x1,y1,m1)
    L=x1-x0; t=(x-x0)./L;
    y =(2*t.^3-3*t.^2+1)*y0+(t.^3-2*t.^2+t)*L*m0+(-2*t.^3+3*t.^2)*y1+(t.^3-t.^2)*L*m1;
    dy=((6*t.^2-6*t)*y0+(3*t.^2-4*t+1)*L*m0+(-6*t.^2+6*t)*y1+(3*t.^2-2*t)*L*m1)./L;
end

%[appendix]{"version":"1.0"}
%---
