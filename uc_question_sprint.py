import pandas as pd

disc = pd.read_csv('uc_freshman_admission_by_discipline.csv')
eth = pd.read_csv('uc_admissions_summary_by_ethnicity.csv')
dash = pd.read_csv('dashboard_data.csv', low_memory=False)

f = eth[(eth.fall_term == 2025) & (eth.entrant_level == 'freshman') & (eth.count_type == 'App')]
unique_applicants = f[f.campus == 'Systemwide'].n.sum()
total_apps = f[f.campus != 'Systemwide'].n.sum()
q1 = round(total_apps / unique_applicants, 2)
print("Q1:", q1)

ucla = dash[(dash.campus == 'Los Angeles') & (dash.fall_term == 2025) & dash.school_type.str.contains('Public', na=False)]
q2 = round(ucla.admits.sum() / ucla.applicants.sum() * 100, 2)
print("Q2:", q2)

cs = disc[disc.broad_discipline == 'Computer Science'][['campus', 'admit_rate']]
overall = disc[disc.broad_discipline == 'All disciplines'][['campus', 'admit_rate']]
gap = cs.merge(overall, on='campus', suffixes=('_cs', '_all'))
gap['drop'] = gap.admit_rate_all - gap.admit_rate_cs
q3 = gap.loc[gap['drop'].idxmax(), 'campus']
print("Q3:", q3)

bcs = disc[(disc.campus == 'Berkeley') & (disc.broad_discipline == 'Computer Science')].iloc[0]
q4 = round(bcs.admit_gpa_p75 - bcs.admit_gpa_p25, 2)
print("Q4:", q4)

e = eth[(eth.fall_term == 2025) & (eth.entrant_level == 'freshman')]
piv = e.pivot_table(index='campus', columns=['count_type', 'ethnicity'], values='n')

def admit_rate(campus, group):
    return piv.loc[campus, ('Adm', group)] / piv.loc[campus, ('App', group)]

campuses = ['Berkeley', 'Davis', 'Irvine', 'Los Angeles', 'Merced', 'Riverside', 'San Diego', 'Santa Barbara', 'Santa Cruz']
q5 = sum(admit_rate(c, 'White') > admit_rate(c, 'Hispanic/Latino(a)') for c in campuses)
print("Q5:", q5)

q6 = 'White' if admit_rate('Systemwide', 'White') > admit_rate('Systemwide', 'Hispanic/Latino(a)') else 'Hispanic/Latino(a)'
print("Q6:", q6)

d23 = dash[dash.fall_term == 2023].drop_duplicates('cds_code')
q7 = round(d23.enrolled_ccc.sum() / d23.hs_completers.sum() * 100, 2)
print("Q7:", q7)

msj = dash[(dash.high_school.str.contains('MISSION SAN JOSE', na=False)) & (dash.fall_term == 2023) & (dash.campus == 'Universitywide')].iloc[0]
q8 = round(msj.applicants / msj.ag_completers * 100, 2)
print("Q8:", q8)

q9 = dash[(dash.fall_term == 2025) & (dash.campus == 'Universitywide') & (dash.applicants > 0)].cds_code.nunique()
print("Q9:", q9)
