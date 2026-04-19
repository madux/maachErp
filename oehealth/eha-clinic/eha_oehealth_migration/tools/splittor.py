import logging

_logger = logging.getLogger(__name__)

def splittor(rs):
    # TODO: get the batch size from configuration later
    batch_size = 100
    batch = 1
    for idx in range(0, len(rs), batch_size):
        _logger.info(
            f"-------------- Processing batch {batch} --------------")
        sub = rs[idx:idx+batch_size]
        for record in sub:
            yield record
        rs.invalidate_cache(ids=sub.ids)
        batch += 1