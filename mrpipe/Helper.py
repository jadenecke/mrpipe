

class Helper(object):
    @staticmethod
    def flatten(lst):
        result = []
        for i in lst:
            if isinstance(i, list):
                result.extend(Helper.flatten(i))
            else:
                result.append(i)
        return result

    @staticmethod
    def ensure_list(x, flatten=False):
        if isinstance(x, list):
            if flatten:
                return Helper.flatten(x)
            else:
                return x
        else:
            return [x]


    @staticmethod
    def shorten_name(name: str, n=8):
        # Split the filename into words
        words = name.split('_')

        # Calculate the number of characters to take from each word
        num_chars = n // len(words)

        # Shorten each word and join them together
        shortened_words = [word[:num_chars] for word in words]
        shortened_filename = ''.join(shortened_words)

        # If the filename is still too long, truncate it
        if len(shortened_filename) > n:
            shortened_filename = shortened_filename[:n]

        return shortened_filename
