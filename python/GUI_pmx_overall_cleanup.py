
import pmx_overall_cleanup
import graphic_user_interface

if __name__ == '__main__':
	graphic_user_interface.launch_gui("PMX Overall Cleanup",
									  pmx_overall_cleanup.showallhelp,
									  pmx_overall_cleanup.pmx_overall_cleanup,
									  pmx_overall_cleanup.end,
									  ("pmx",))
