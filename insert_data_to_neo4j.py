from langchain_community.graphs import Neo4jGraph
# Instantiate connection to Neo4j
graph = Neo4jGraph(url='bolt://localhost:7687', username='neo4j', password='123')
# Define unique constraints
graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE;")
graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;")
graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE;")
graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE;")

# Import movie information

movies_query = """
CALL apoc.periodic.iterate(
'CALL apoc.load.csv("movies.csv",{header:true,sep:","}) YIELD map AS row RETURN row',
'MERGE (m:Movie {id:row.movieId})
    SET m.released = date(row.released),
        m.title = row.title,
        m.imdbRating = toFloat(row.imdbRating)
    FOREACH (director in split(row.director, "|") |
        MERGE (p:Person {name:trim(director)})
        MERGE (p)-[:DIRECTED]->(m))
    FOREACH (actor in split(row.actors, "|") |
        MERGE (p:Person {name:trim(actor)})
        MERGE (p)-[:ACTED_IN]->(m))
    FOREACH (genre in split(row.genres, "|") | 
        MERGE (g:Genre {name:trim(genre)})
        MERGE (m)-[:IN_GENRE]->(g))',
{batchSize:1000, parallel:false}) YIELD batches, total
RETURN batches, total
"""
graph.query(movies_query)

# Import rating information
rating_query = """
CALL apoc.periodic.iterate(
'CALL apoc.load.csv("ratings.csv",{header:true,sep:","}) YIELD map AS row RETURN row',
'MATCH (m:Movie {id:row.movieId})
    MERGE (u:User {id:row.userId})
    MERGE (u)-[r:RATED]->(m)
    SET r.rating = toFloat(row.rating),
        r.timestamp = row.timestamp',
{batchSize:1000, parallel:false}) YIELD batches, total
RETURN batches, total
"""

graph.query(rating_query)

# Define fulltext indices
graph.query("CALL db.index.fulltext.createNodeIndex('movie',['Movie'], ['title'],{ analyzer: 'cjk'})")
graph.query("CALL db.index.fulltext.createNodeIndex('person',['Person'], ['name'],{ analyzer: 'cjk'})")
