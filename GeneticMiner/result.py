import pm4py
net, im, fm = pm4py.read_pnml('output/result_petri_net.pnml')
# pm4py.view_petri_net(net, im, fm)
pm4py.save_vis_petri_net(net, im, fm, 'output/result_petri_net_view.png')