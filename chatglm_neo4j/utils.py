from py2neo import Graph

graph = Graph('http://localhost:7474', auth=("neo4j", "123"))

def get_candidates(name: str):
    answer = graph.run(
        "MATCH (m:Movie)<-[rel:ACTED_IN]-(p:Person) where p.name = $name return rel", name=name).data()
    answer_name = []
    for an in answer:
        rel = an['rel']
        end_name = rel.end_node['title']
        answer_name.append(end_name)
    if len(answer_name) == 0:
        return []
    return answer_name

def get_candidates2(genre: str):
    answer = graph.run(
        "MATCH (m:Movie)-[rel:IN_GENRE]->(g:Genre) where g.name = $name return rel", name=genre).data()
    answer_name = []
    for an in answer:
        rel = an['rel']
        start_name = rel.start_node['title']
        answer_name.append(start_name)
    if len(answer_name) == 0:
        return []
    return answer_name

fulltext_search_query = """
CALL db.index.fulltext.queryNodes($index, $fulltextQuery)
YIELD node
RETURN coalesce(node.name) AS candidate,
       [el in labels(node) WHERE el IN ['Person'] | el][0] AS label
"""

def fulltext_search_query_get_entity(input: str, type: str):
    candidates = graph.query(
        fulltext_search_query, {"index": type, "fulltextQuery": input}
    )
    return candidates

