from planpro_importer import PlanProVersion, import_planpro
from railwayroutegenerator.routegenerator import RouteGenerator
from sumoexporter import SUMOExporter

topology = import_planpro("test.ppxml", PlanProVersion.PlanPro19)
print("topology:")
print(len(topology.edges))
print(len(topology.signals))

generator = RouteGenerator(topology)
generator.generate_routes()
print(topology.routes)

sumo_exporter = SUMOExporter(topology)
sumo_exporter.convert()
sumo_exporter.write_output()
