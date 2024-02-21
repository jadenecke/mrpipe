

class Helper(object):
    @classmethod
    def flatten(cls, lst):
        result = []
        for i in lst:
            if isinstance(i, list):
                result.extend(Helper.flatten(i))
            else:
                result.append(i)
        return result

    @classmethod
    def ensure_list(cls, x, flatten=False):
        if isinstance(x, list):
            if flatten:
                return Helper.flatten(x)
            else:
                return x
        else:
            return [x]


