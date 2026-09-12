import os

base_dir = r"C:\Users\indra\Documents\hello_world\ResearchGraph"
routes_path = os.path.join(base_dir, 'app/main/routes.py')

with open(routes_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_route = """
@main_bp.route('/welcome')
def welcome():
    form = SearchForm()
    return render_template('welcome.html', form=form)
"""

if "def welcome():" not in content:
    with open(routes_path, 'a', encoding='utf-8') as f:
        f.write(new_route)
    print("welcome route added.")
