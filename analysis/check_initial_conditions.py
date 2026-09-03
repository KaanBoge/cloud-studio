import yt, numpy as np
yt.set_log_level(50)
ds = yt.load("/home/kaan/codes/flashx/runs/smoke3d/smoke3d_hdf5_plt_cnt_0000")
print("domain_left ", ds.domain_left_edge)
print("domain_right", ds.domain_right_edge)
print("dims level0 ", ds.domain_dimensions)
print("max level   ", ds.index.max_level)
eff = ds.domain_dimensions * 2**ds.index.max_level
print("effective   ", eff)
# ray along +z through the cloud centre
ray = ds.ray([0.0,0.0,0.0],[0.0,0.0,5.0])
z = np.array(ray["gas","z"]); srt = np.argsort(z)
z = z[srt]
d = np.array(ray["flash","dens"])[srt]
vx = np.array(ray["flash","velx"])[srt]
print("\n   r      dens      velx")
for r in [0.5,0.9,1.0,1.1,1.2,1.3,1.4,1.6,2.0]:
    i = np.argmin(abs(z-r))
    print("%5.2f  %8.4f  %8.4f" % (z[i], d[i], vx[i]))
# where does velx cross half the wind speed?
vw = 2.582
i = np.argmin(abs(vx - 0.5*vw))
print("\nvelx = vw/2 (%.4f) nearest at r = %.4f  <-- velocity transition" % (0.5*vw, z[i]))
j = np.argmin(abs(d - 5.5))
print("dens = 5.5 (half) nearest at r = %.4f  <-- density edge" % z[j])
