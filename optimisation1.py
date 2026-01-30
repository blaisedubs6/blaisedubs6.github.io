import math
from pyomo.environ import *

# -------------------------
# Données
# -------------------------
patients = {
    1: {"weight": 70},
    2: {"weight": 55},
    3: {"weight": 90},
    4: {"weight": 62},
}

alpha = 2.0          # MBq/kg
slot_duration = 20   # minutes

K = 30               # nb de slots dispo (doit être >= N)
start_time = 8 * 60  # 08:00
slots = [start_time + k * slot_duration for k in range(K)]

delivery_time = 8*60  # 8:00
A0 = 4000
half_life = 110
lam = math.log(2) / half_life

D = {i: alpha * patients[i]["weight"] for i in patients}
P_list = list(patients.keys())
N = len(P_list)

delta = math.exp(-lam * slot_duration)

# Stock disponible juste AVANT le 1er slot (donc déjà décroît depuis la livraison)
S0 = A0 * math.exp(-lam * (slots[0] - delivery_time))

if N > K:
    raise ValueError("Il faut K >= nombre de patients (N).")

# -------------------------
# Modèle
# -------------------------
m = ConcreteModel()
m.P = Set(initialize=P_list)
m.K = RangeSet(0, K - 1)

m.x = Var(m.P, m.K, domain=Binary)           # patient i au slot k
m.y = Var(m.P, m.K, domain=NonNegativeReals) # MBq injectés à i au slot k
m.u = Var(m.K, domain=Binary)                # slot k utilisé
m.S = Var(m.K, domain=NonNegativeReals)      # stock AVANT injection au slot k

# -------------------------
# Contraintes
# -------------------------

# 1 patient par slot si slot utilisé (sinon aucun)
def one_patient_per_slot(m, k):
    return sum(m.x[i, k] for i in m.P) == m.u[k]
m.c1 = Constraint(m.K, rule=one_patient_per_slot)

# chaque patient exactement une fois
def one_slot_per_patient(m, i):
    return sum(m.x[i, k] for k in m.K) == 1
m.c2 = Constraint(m.P, rule=one_slot_per_patient)

# dose fixe par patient
def dose_constraint(m, i):
    return sum(m.y[i, k] for k in m.K) == D[i]
m.c3 = Constraint(m.P, rule=dose_constraint)

# lien y <= D_i * x
def linking(m, i, k):
    return m.y[i, k] <= D[i] * m.x[i, k]
m.c4 = Constraint(m.P, m.K, rule=linking)

# stock initial
m.c5 = Constraint(expr=m.S[0] == S0)

# pas consommer plus que stock dispo au slot k
def cannot_use_more_than_stock(m, k):
    return sum(m.y[i, k] for i in m.P) <= m.S[k]
m.c6 = Constraint(m.K, rule=cannot_use_more_than_stock)

# dynamique correcte: on enlève l'injection, puis décroissance
def stock_flow(m, k):
    if k == K - 1:
        return Constraint.Skip
    used_k = sum(m.y[i, k] for i in m.P)
    return m.S[k + 1] == (m.S[k] - used_k) * delta
m.c7 = Constraint(m.K, rule=stock_flow)

# exactement N slots utilisés (on injecte N patients)
m.c8 = Constraint(expr=sum(m.u[k] for k in m.K) == N)

# pas de trous: si slot k utilisé alors k-1 utilisé
def no_gaps(m, k):
    if k == 0:
        return Constraint.Skip
    return m.u[k] <= m.u[k - 1]
m.c9 = Constraint(m.K, rule=no_gaps)

# donc slots utilisés = 0..N-1, dernier patient au slot last_k
last_k = N - 1

# -------------------------
# Objectif
# -------------------------
# stock juste APRES le dernier patient (sans décroissance après)
used_last = sum(m.y[i, last_k] for i in m.P)
m.obj = Objective(expr=m.S[last_k] - used_last, sense=maximize)

# -------------------------
# Solve
# -------------------------
solver = SolverFactory("cbc")  # ou "glpk"
solver.solve(m, tee=True)

# -------------------------
# Affichage
# -------------------------
def fmt_time(minutes):
    return f"{minutes//60:02d}:{minutes%60:02d}"

print("\n=== Planning injections (slots utilisés) ===")
for k in range(K):
    if value(m.u[k]) > 0.5:
        for i in m.P:
            if value(m.x[i, k]) > 0.5:
                dose = value(m.y[i, k])
                stock_before = value(m.S[k])
                print(f"slot {k:02d}  {fmt_time(slots[k])}  patient {i}  dose={dose:.1f} MBq  stock_avant={stock_before:.1f}")
                break

stock_after_last = value(m.S[last_k]) - sum(value(m.y[i, last_k]) for i in m.P)
print("\nStock juste après dernier patient (objectif) :", stock_after_last)