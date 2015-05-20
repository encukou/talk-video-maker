import numpy as np

cimport numpy as cnp
cimport cython

DTYPE = np.float
ctypedef cnp.float_t DTYPE_t


@cython.boundscheck(False)
@cython.wraparound(False)
def dtw(input1, input2):
    cdef DTYPE_t[:, ::1] a = np.array(input1, dtype=DTYPE, order='C')
    cdef DTYPE_t[:, ::1] b = np.array(input2, dtype=DTYPE, order='C')

    cdef unsigned int a_len = a.shape[0]
    cdef unsigned int b_len = b.shape[0]
    cdef unsigned int v_len = a.shape[1]
    assert v_len == b.shape[1]
    cdef DTYPE_t[:, ::1] cost = np.zeros([a_len, b_len], dtype=DTYPE, order='C')
    cdef unsigned int i, j, k
    cdef DTYPE_t s, t, u
    cdef unsigned int bt_len = a_len + b_len
    cdef cnp.uint_t[::1] path_a = np.zeros([bt_len], dtype=np.uint, order='C')
    cdef cnp.uint_t[::1] path_b = np.zeros([bt_len], dtype=np.uint, order='C')

    with nogil:
        # Cython currently does not check if Python objects are manipulated
        # inside a "nogil" block. When changing this, double-check your work!

        # Fill cost matrix with the cost for each element
        # The cost is the L-1 (Manhattan) norm of the difference (that is,
        # sums of absolute values of differences between respective elements)
        # The array starts zeroed out
        for i in range(a_len):
            for j in range(b_len):
                for k in range(v_len):
                    s = a[i, k] - b[j, k]
                    if s > 0:
                        cost[i, j] += s
                    else:
                        cost[i, j] -= s

        # Sum up first row & column
        # These are running totals of the respective costs -- special case of
        # the nested loop below
        for i in range(1, a_len):
            cost[i, 0] = cost[i-1, 0] + cost[i, 0]
        for j in range(1, b_len):
            cost[0, j] = cost[0, j-1] + cost[0, j]

        # Fill rest of array
        # Cell c[x,y] is assigned (min(c[x-1,y-1], c[x-1,y], c[x,y-1]) + cost(x, y))
        # where cost(x, y) is already filled in
        for i in range(1, a_len):
            for j in range(1, b_len):
                s = cost[i-1, j-1]

                t = cost[i, j-1]
                if t < s:
                    s = t

                t = cost[i-1, j]
                if t < s:
                    s = t

                cost[i, j] += s

        # Backtrack
        # Fill "path_a" and "path_b" arrays backwards from the end with
        # indices of the backtracked path; then return only the parts filled
        i = a_len - 1
        j = b_len - 1
        k = bt_len - 1
        while i and j:
            path_a[k] = i
            path_b[k] = j
            k -= 1
            s = cost[i-1, j-1]
            t = cost[i, j-1]
            u = cost[i-1, j]
            # which is smallest?  (want to prefer s in case of tie)
            if s <= t:  # it's not t
                if s <= u:  # s is smallest
                    i -= 1
                    j -= 1
                else:  # u is smallest
                    i -= 1
            else:  # it's not s
                if t <= u:  # t is smallest
                    j -= 1
                else:  # s is smallest
                    i -= 1
        while i:
            path_a[k] = i
            path_b[k] = j
            k -= 1
            i -= 1
        while j:
            path_a[k] = i
            path_b[k] = j
            k -= 1
            j -= 1

    dist = cost[a_len-1, b_len-1] / (a_len + b_len)

    return dist, cost, np.array([path_a[k:], path_b[k:]], dtype=np.uint)
