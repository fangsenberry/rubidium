original search queries refer to those that are being sourced for without intereference/whatever from the saturday call notes. The other one comes directly from what was being talked about in the sat call notes

the metadata for the searching function just follows the following for now:
its a cartesian product between all of the sets, which is to say
queries (literally each query) X websites X success/failure (for the website search) X success/failure (for the ujeebu search) X response code (for the ujeebu thing) X relevance (for the result from ujeebu) X time taken (for the ujeebu thing) + one last field for the content that it has returned. this will majorly help with footnoting.

#TODO: change this doc to latex

metadata for searching formalised:
1 query
n websites for each query
n success/failure for each website [STATUS]
number of links retrieved for each website
n success/failure for each ujeebu search
n response codes for each ujeebu search
summarisation cost (if it goes into summarisation, else this cost will be 0) (or the field will not exist? idk)
n relevance for each ujeebu search
cost for relevance
n time taken for each ujeebu search
n content for each ujeebu search

i think each query needs a hash? i don't want to override things, but for now we will proceed without a hash.

TODO: the link getting and link ujeebu should be same thread, that way we don't need to wait for all the websites to retrieve before getting, also will clean up the metadata structure a bit.